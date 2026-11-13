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
        let
          caPython = pkgs.python314.withPackages (python-pkgs: [ python-pkgs.python-dotenv ]);
        in
        {
          langfuse-review-queue = pkgs.writeShellApplication {
            name = "langfuse-review-queue";
            runtimeInputs = [ pkgs.python314 ];
            text = ''
              export PYTHONPATH=${self}
              exec python -P -m core.langfuse_review "$@"
            '';
          };
          # Interactive by default: renders the live stderr progress view and
          # writes only a private proposal. The systemd timer below explicitly
          # selects --headless because it has no terminal to paint.
          ca-improve = pkgs.writeShellApplication {
            name = "ca-improve";
            runtimeInputs = [
              caPython
              pkgs.nodejs
            ];
            text = ''
              export PYTHONPATH=${self}
              exec python -P -m core improve-run "$@"
            '';
          };
          ca = pkgs.writeShellApplication {
            name = "ca";
            runtimeInputs = [ caPython ];
            text = ''
              export PYTHONPATH=${self}
              exec python -P -m core "$@"
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

      # Home Manager module: the living SOUL and the weekly improvement pass
      # run as the same user as Hermes. The repo ships the bootstrap SOUL;
      # everything that changes afterwards lives under the CA state dir.
      homeManagerModules.cognitive-assistant =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        let
          cfg = config.services.cognitive-assistant;
          system = pkgs.stdenv.hostPlatform.system;
          prefixFile = pkgs.writeText "ca-soul-prefix.md" cfg.soul.prefix;
          suffixFile = pkgs.writeText "ca-soul-suffix.md" cfg.soul.suffix;
        in
        {
          options.services.cognitive-assistant = {
            enable = lib.mkEnableOption "the Cognitive Assistant living SOUL for Hermes";
            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${system}.ca;
              description = "CA CLI (`python -m core`) carrying the bootstrap SOUL.";
            };
            improvePackage = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${system}.ca-improve;
            };
            hermesHome = lib.mkOption {
              type = lib.types.str;
              example = "/home/codyt/.local/share/hermes";
              description = ''
                HERMES_HOME. Its SOUL.md becomes a symlink to the living SOUL, so
                SOUL.md must not also be declared in hermesHomeFiles. User units
                do not inherit login-shell session variables, so the improvement
                pass gets it from here.
              '';
            };
            soul.prefix = lib.mkOption {
              type = lib.types.lines;
              default = "";
              description = "Deployer text placed before the SOUL in every generation.";
            };
            soul.suffix = lib.mkOption {
              type = lib.types.lines;
              default = "";
              description = "Deployer text placed after the SOUL in every generation.";
            };
            improve.enable = lib.mkOption {
              type = lib.types.bool;
              default = true;
              description = "Run the headless improvement pass on a timer.";
            };
            improve.auto = lib.mkOption {
              type = lib.types.bool;
              default = true;
              description = ''
                Adopt and revert changes without review: each run judges the change
                under test by Hermes session miss rate, reverts it when sessions got
                significantly worse, and otherwise adopts one kept record.
              '';
            };
            improve.minSessions = lib.mkOption {
              type = lib.types.ints.positive;
              default = 15;
              description = "Analyzed Hermes sessions needed on each side before a change is judged.";
            };
            llm.baseUrl = lib.mkOption {
              type = lib.types.str;
              example = "http://127.0.0.1:8080/v1";
              description = ''
                OpenAI-compatible endpoint for the improvement pass. Each stage is one
                tool-free chat completion; nothing is executed on the model's behalf.
              '';
            };
            llm.model = lib.mkOption {
              type = lib.types.str;
              example = "qwen-3.6-35b-a3b";
              description = "Model for every stage unless overridden in llm.roleModels.";
            };
            llm.roleModels = lib.mkOption {
              type = lib.types.attrsOf lib.types.str;
              default = { };
              example = {
                synthesis = "a-larger-model";
                annotate = "a-larger-model";
              };
              description = "Per-stage model overrides: analysis, consolidate, synthesis, annotate.";
            };
            llm.apiKeyFile = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "File holding a bearer key, for a hosted endpoint. Use an inference-only key.";
            };
            improve.harnesses = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              default = [ "hermes" ];
              description = "Harnesses to scan; a named harness with a missing store fails the run.";
            };
            improve.timerConfig = lib.mkOption {
              type = lib.types.attrs;
              default = {
                OnCalendar = "weekly";
                Persistent = true;
              };
            };
          };
          config = lib.mkIf cfg.enable {
            home.packages = [ cfg.package ];

            # Rebuild the living SOUL from the (possibly new) bootstrap plus
            # lineage, then point Hermes at it. Idempotent: no new generation
            # unless the inputs changed.
            home.activation.cognitiveAssistantSoul = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
              run ${cfg.package}/bin/ca soul compile \
                --prefix-file ${prefixFile} --suffix-file ${suffixFile} --reason activation
              run ${cfg.package}/bin/ca soul link ${lib.escapeShellArg cfg.hermesHome}
            '';

            systemd.user.services.ca-improve = lib.mkIf cfg.improve.enable {
              Unit.Description = "CA headless improvement pass over Hermes sessions";
              Service = {
                Type = "oneshot";
                Environment = [
                  "HERMES_HOME=${cfg.hermesHome}"
                  "CA_LLM_BASE_URL=${cfg.llm.baseUrl}"
                  "CA_LLM_MODEL=${cfg.llm.model}"
                ]
                ++ lib.mapAttrsToList (role: model: "CA_LLM_MODEL_${lib.toUpper role}=${model}") cfg.llm.roleModels
                ++ lib.optional (cfg.llm.apiKeyFile != null) "CA_LLM_API_KEY_FILE=${cfg.llm.apiKeyFile}";
                ExecStart = lib.escapeShellArgs (
                  [
                    "${cfg.improvePackage}/bin/ca-improve"
                    "--headless"
                  ]
                  ++ lib.optionals cfg.improve.auto [
                    "--auto"
                    "--min-sessions"
                    (toString cfg.improve.minSessions)
                  ]
                  ++ lib.concatMap (harness: [
                    "--harness"
                    harness
                  ]) cfg.improve.harnesses
                );
              };
            };
            systemd.user.timers.ca-improve = lib.mkIf cfg.improve.enable {
              Unit.Description = "Weekly CA improvement pass";
              Timer = cfg.improve.timerConfig;
              Install.WantedBy = [ "timers.target" ];
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
              (pkgs.python314.withPackages (
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
              pkgs.nodejs
              ai-data-extractor.packages.${pkgs.stdenv.hostPlatform.system}.default
            ];
          };
        }
      );
    };
}
