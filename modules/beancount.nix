{
  homeModule = { pkgs, ... }: {
    home.packages = builtins.attrValues {
      inherit (pkgs) beancount fava;
    };
  };
}
