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
      skillsDir = ./workspaces/skills;
      skillCategories = builtins.attrNames (
        nixpkgs.lib.filterAttrs (_: fileType: fileType == "directory") (builtins.readDir skillsDir)
      );
      skillNamesByCategory = nixpkgs.lib.genAttrs skillCategories (
        category:
        builtins.attrNames (
          nixpkgs.lib.filterAttrs
            (_: fileType: fileType == "directory")
            (builtins.readDir (skillsDir + "/${category}"))
        )
      );
      skillEntries = builtins.concatLists (
        map (
          category:
          map (
            name:
            {
              inherit category name;
              path = skillsDir + "/${category}/${name}/SKILL.md";
            }
          ) skillNamesByCategory.${category}
        ) skillCategories
      );
      skillsByName = builtins.listToAttrs (
        map (
          entry:
          {
            name = entry.name;
            value = entry.path;
          }
        ) skillEntries
      );
      categorizedSkills = pkgs: pkgs.linkFarm "hermes-skills" (
        map (
          entry:
          {
            name = "${entry.category}/${entry.name}/SKILL.md";
            path = entry.path;
          }
        ) skillEntries
      );
      skills = pkgs: pkgs.linkFarm "opencode-skills" (
        map (
          entry:
          {
            name = "${entry.name}/SKILL.md";
            path = entry.path;
          }
        ) skillEntries
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
        inherit existential operational;
        layers = {
          inherit existential operational;
        };
        alignment = {
          spec = ./workspaces/alignment/artifacts/alignment_spec.md;
          soulFile = ./workspaces/alignment/artifacts/SOUL.md;
          toolSpecs = {
            verifyAlignment = ./workspaces/alignment/artifacts/tool_specs/verify_alignment.md;
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
          skills = skills pkgs;
          categorizedSkills = categorizedSkills pkgs;
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
