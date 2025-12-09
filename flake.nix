{
  description = "A Nix-flake-based Python development environment";

  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.*.tar.gz";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        pkgs = import nixpkgs { inherit system; };
      });
    in
    {
      devShells = forEachSupportedSystem ({ pkgs }: {
        default = pkgs.mkShell {
          venvDir = ".venv";
          packages = with pkgs; [ python312 ] ++
             (with pkgs.python312Packages; [
               pip
               venvShellHook
               python-dotenv
               langchain-openai
               langchain-core
               langchain-community
               langgraph
               notebook
               jupyter
               pandas
               scikit-learn
               streamlit
             ]);
          shellHook = ''
            if [ ! -d ".venv" ]; then
              python -m venv .venv
              source .venv/bin/activate
              pip install -r requirements.txt
            else
              source .venv/bin/activate
            fi
          '';
        };
      });
    };
}
