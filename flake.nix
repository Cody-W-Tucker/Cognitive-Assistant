{
  description = "Cognitive Assistant flake outputs and development environment";

  inputs = {
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.*.tar.gz";
    rlm.url = "github:Cody-W-Tucker/rlm";
    ai-data-extractor.url = "github:Cody-W-Tucker/ai-data-extraction";
  };

  outputs =
    {
      self,
      nixpkgs,
      rlm,
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
            pkgs = import nixpkgs { inherit system; };
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

      # --- Agent souls ---
      agentsDir = ./workspaces/alignment/artifacts/agents;
      agentFilesRaw = if builtins.pathExists agentsDir then builtins.readDir agentsDir else { };
      agentSoulEntries = builtins.filter
        (entry: entry.type == "regular" && builtins.match ".*\\.md$" entry.name != null && entry.name != "README.md")
        (nixpkgs.lib.mapAttrsToList (name: type: { inherit name type; }) agentFilesRaw);
      agentSoulsByName = builtins.listToAttrs (
        map
          (entry: {
            name = builtins.replaceStrings [ ".md" ] [ "" ] entry.name;
            value = builtins.readFile (agentsDir + "/${entry.name}");
          })
          agentSoulEntries
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
      lib = {
        artifacts = {
          alignment = {
            spec = ./workspaces/alignment/artifacts/alignment_spec.md;
            translationLayer = ./workspaces/alignment/artifacts/SOUL.md;
            interactionPosture = ./workspaces/alignment/artifacts/INTERACTION_POSTURE.md;
            # persona_map.md is a generated plan projection: it exists only
            # after `build-agents` commits an agent_plan.json.
          }
          // nixpkgs.lib.optionalAttrs
            (builtins.pathExists ./workspaces/alignment/artifacts/persona_map.md)
            { personaMap = ./workspaces/alignment/artifacts/persona_map.md; }
          // {
            agentSouls = agentSoulsByName;
            agentSoulNames = builtins.attrNames agentSoulsByName;
            toolSpecs = {
              verifyAlignment = ./workspaces/alignment/artifacts/tool_specs/verify_alignment.md;
            };
          };
          inherit existential operational;
          skills = {
            names = builtins.attrNames skillsByName;
            files = skillsByName;
            categorized = skillsDir;
          };
        };
      };

      packages = forEachSupportedSystem (
        { pkgs }:
        {
          verify-alignment = pkgs.writeShellApplication {
            name = "verify-alignment";
            runtimeInputs = [ rlm.packages.${pkgs.stdenv.hostPlatform.system}.default ];
            text = ''
              ALIGNMENT_SPEC="''${ALIGNMENT_SPEC:-${./workspaces/alignment/artifacts/alignment_spec.md}}"
              export ALIGNMENT_SPEC
              exec ${./scripts/verify_alignment.sh} "$@"
            '';
          };
        }
      );

      devShells = forEachSupportedSystem (
        { pkgs }:
        {
          default = pkgs.mkShell {
            packages = [
              (pkgs.python312.withPackages (
                python-pkgs: with python-pkgs; [
                  python-dotenv
                  anthropic
                  pandas
                  openai
                ]
              ))
              rlm.packages.${pkgs.stdenv.hostPlatform.system}.default
              ai-data-extractor.packages.${pkgs.stdenv.hostPlatform.system}.default
            ];
          };
        }
      );
    };
}
