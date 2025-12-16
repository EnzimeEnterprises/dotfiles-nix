self: super: {
  ranger = super.ranger.overrideAttrs (old:
    let
      #                       (a == b)   (a > b)
      # compareVersions a b =       0  |      1
      versionAtMost = a: b: builtins.compareVersions a b > -1;
    in {
      # Using OSC 52 for clipboard instead of xclip
      # SEE: https://github.com/NixOS/nixpkgs/pull/141466#issuecomment-942185842
      # SEE ALSO: https://github.com/ranger/ranger/issues/2404

      patches = assert (versionAtMost "1.9.4" old.version);
        (old.patches or [ ]) ++ [
          (super.fetchpatch {
            name = "fix-ctrl-arrows.patch";
            url =
              "https://github.com/Enzime/ranger/commit/9e60541f3e360e2019d0b671852249771b843761.patch";
            hash = "sha256-R3Qia9++n8SC/fG72GwLYbjwmx/oyEm5BfC2/6nziqI=";
          })
        ];
    });

  ranger-oscyank = super.fetchFromGitHub {
    owner = "laggardkernel";
    repo = "ranger-oscyank";
    rev = "4bd84de5fde0b7edb223d62a5a4ee9ef4f1fe472";
    hash = "sha256-Vc1/5AvqKEu4bORE8FXhRkJvbpauDXQJvqB4xYHYgBQ=";
  };
}
