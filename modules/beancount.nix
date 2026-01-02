{
  homeModule =
    { pkgs, config, lib, ... }:
    let
      # Python environment with beancount and importers
      pythonWithBeancount = pkgs.python3.withPackages (ps: [
        ps.beancount
        ps.beangulp
        ps.smart-importer
        # Add more importer packages as they become available in nixpkgs
      ]);

      # Directory containing custom importers
      importersDir = ../files/beancount;
    in
    {
      home.packages = [
        pythonWithBeancount
        pkgs.fava
      ];

      # Copy custom importers to ~/.config/beancount/
      xdg.configFile = {
        "beancount/importers/__init__.py".source =
          "${importersDir}/importers/__init__.py";
        "beancount/importers/commbank.py".source =
          "${importersDir}/importers/commbank.py";
        "beancount/importers/ubank.py".source =
          "${importersDir}/importers/ubank.py";
        "beancount/importers/pearler.py".source =
          "${importersDir}/importers/pearler.py";
        "beancount/importers/selfwealth.py".source =
          "${importersDir}/importers/selfwealth.py";
        "beancount/importers/scalable.py".source =
          "${importersDir}/importers/scalable.py";
        "beancount/import_config.py".source =
          "${importersDir}/import_config.py";
      };
    };
}
