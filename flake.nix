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
        workspaceDir:
        let
          skillsDir = workspaceDir + "/artifacts/skills";
          systemPromptFile = workspaceDir + "/artifacts/system_prompt.md";
          skillNames = builtins.attrNames (
            nixpkgs.lib.filterAttrs (_: fileType: fileType == "directory") (builtins.readDir skillsDir)
          );
        in
        {
          inherit skillsDir systemPromptFile skillNames;
          skillFile = name: skillsDir + "/${name}/SKILL.md";
        };
      existential = mkLayerExports ./workspaces/existential;
      operational = (mkLayerExports ./workspaces/operational) // {
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
