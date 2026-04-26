{
  description = "Cognitive Assistant flake outputs and development environment";

  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.*.tar.gz";
  inputs.rlm.url = "github:Cody-W-Tucker/rlm";

  outputs =
    { self, nixpkgs, rlm }:
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
      artifactsDir = ./Existential-Layer/artifacts;
      skillsDir = ./Existential-Layer/artifacts/skills;
      systemPromptFile = ./Existential-Layer/artifacts/system_prompt.md;
      humanProfileFile = ./Existential-Layer/artifacts/human_profile.md;
    in
    {
      lib = {
        inherit artifactsDir skillsDir systemPromptFile humanProfileFile;
        skillFile = name: skillsDir + "/${name}/SKILL.md";
      };

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
              rlm.packages.${pkgs.system}.default
            ];
          };
        }
      );
    };
}
