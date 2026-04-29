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
      skillsDir = ./Existential-Layer/artifacts/skills;
      systemPromptFile = ./Existential-Layer/artifacts/system_prompt.md;
    in
    {
      lib = {
        inherit skillsDir systemPromptFile;
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
              ai-data-extractor.packages.${pkgs.system}.default
            ];
          };
        }
      );
    };
}
