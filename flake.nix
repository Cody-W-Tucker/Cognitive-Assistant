{
  description = "Cognitive Assistant flake outputs and development environment";

  inputs = {
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.*.tar.gz";
    llm-agents.url = "github:numtide/llm-agents.nix";
    ai-data-extractor.url = "github:Cody-W-Tucker/ai-data-extraction";
  };

  outputs =
    {
      self,
      nixpkgs,
      llm-agents,
      ai-data-extractor,
    }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSupportedSystem =
        f:
        nixpkgs.lib.genAttrs supportedSystems (
          system:
          f {
            pkgs = import nixpkgs {
              inherit system;
              overlays = [ llm-agents.overlays.shared-nixpkgs ];
            };
          }
        );
      mkLayerExports =
        _profileName: workspaceDir:
        let
          humanProfile = workspaceDir + "/artifacts/human_profile.md";
        in
        {
          inherit humanProfile;
        };

      # --- Skills ---
      skillsDir = ./workspaces/skills;
      skillCategories = builtins.attrNames (
        nixpkgs.lib.filterAttrs (_: fileType: fileType == "directory") (builtins.readDir skillsDir)
      );
      skillNamesByCategory = nixpkgs.lib.genAttrs skillCategories (
        category:
        builtins.attrNames (
          nixpkgs.lib.filterAttrs (_: fileType: fileType == "directory") (
            builtins.readDir (skillsDir + "/${category}")
          )
        )
      );
      skillEntries = builtins.concatLists (
        map (
          category:
          map (name: {
            inherit category name;
            path = skillsDir + "/${category}/${name}/SKILL.md";
          }) skillNamesByCategory.${category}
        ) skillCategories
      );
      skillsByName = builtins.listToAttrs (
        map (entry: {
          inherit (entry) name;
          value = builtins.readFile entry.path;
        }) skillEntries
      );

      existential = mkLayerExports "existential" ./workspaces/existential;
      operational = (mkLayerExports "operational" ./workspaces/operational) // {
        toolSpecs = {
          memory = ./workspaces/operational/artifacts/tool_specs/memory.md;
          tasks = ./workspaces/operational/artifacts/tool_specs/tasks.md;
        };
      };
    in
    {
      packages = forEachSupportedSystem (
        { pkgs }:
        {
          langfuse-review-queue = pkgs.writeShellApplication {
            name = "langfuse-review-queue";
            runtimeInputs = [ pkgs.python312 ];
            text = ''
              export PYTHONPATH=${self}
              exec python -m core.langfuse_review "$@"
            '';
          };
          default = self.packages.${pkgs.stdenv.hostPlatform.system}.langfuse-review-queue;
        }
      );

      nixosModules.langfuse-review-queue =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        let
          cfg = config.services.langfuse-review-queue;
        in
        {
          options.services.langfuse-review-queue = {
            enable = lib.mkEnableOption "Langfuse review queue refill";
            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${pkgs.stdenv.hostPlatform.system}.langfuse-review-queue;
            };
            baseUrl = lib.mkOption {
              type = lib.types.str;
              default = "https://cloud.langfuse.com";
            };
            environmentFile = lib.mkOption {
              type = lib.types.path;
              description = "File containing Langfuse credentials.";
            };
            timerConfig = lib.mkOption {
              type = lib.types.attrs;
              default = {
                OnCalendar = "*-*-* 07:00:00 America/Chicago";
                Persistent = true;
              };
            };
          };
          config = lib.mkIf cfg.enable {
            systemd.services.langfuse-review-queue = {
              description = "Refill Langfuse CA routing review queue";
              serviceConfig = {
                ExecStart = "${cfg.package}/bin/langfuse-review-queue";
                EnvironmentFile = cfg.environmentFile;
                Type = "oneshot";
              };
              environment.LANGFUSE_BASE_URL = cfg.baseUrl;
            };
            systemd.timers.langfuse-review-queue = {
              wantedBy = [ "timers.target" ];
              inherit (cfg) timerConfig;
            };
          };
        };

      lib = {
        artifacts = {
          alignment = {
            spec = ./workspaces/alignment/artifacts/alignment_spec.md;
            translationLayer = ./workspaces/alignment/artifacts/SOUL.md;
            interactionPosture = ./workspaces/alignment/artifacts/INTERACTION_POSTURE.md;
          };
          inherit existential operational;
          skills = {
            names = builtins.attrNames skillsByName;
            files = skillsByName;
            categorized = skillsDir;
          };
        };
      };

      devShells = forEachSupportedSystem (
        { pkgs }:
        {
          default = pkgs.mkShell {
            packages = [
              (pkgs.python312.withPackages (
                python-pkgs: with python-pkgs; [
                  python-dotenv
                  pydantic
                  anthropic
                  pandas
                  openai
                ]
              ))
              (pkgs.llm-agents.qmd.override {
                vulkanSupport = false;
                cudaSupport = false;
              })
              ai-data-extractor.packages.${pkgs.stdenv.hostPlatform.system}.default
            ];
          };
        }
      );
    };
}
