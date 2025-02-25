let
  pkgs = import <nixpkgs> {};
  stdenv = pkgs.stdenv;
in pkgs.mkShell {
  LD_LIBRARY_PATH="${stdenv.cc.cc.lib}/lib/";
  buildInputs = [
    (pkgs.python311.withPackages (p: with p; [
      black
      flake8
    ]))
  ];
  shellHook = ''
    if [ ! -d venv ]; then
        python -m venv venv
    fi
  '';
}
