{
  imports = [ "acme" ];

  nixosModule = { options, config, pkgs, lib, ... }:
    let hostname = "readeck.enzim.ee";
    in {
      imports = [{
        config = lib.optionalAttrs (options ? clan) {
          clan.core.vars.generators.readeck = {
            files.env = { };
            runtimeInputs = [ pkgs.coreutils pkgs.openssl ];
            script = ''
              secret=$(openssl rand -hex 32)
              echo "READECK_SECRET_KEY=$secret" > $out/env
            '';
          };
        };
      }];

      services.readeck.enable = true;
      services.readeck.environmentFile =
        config.clan.core.vars.generators.readeck.files.env.path;

      services.readeck.settings = {
        main.log_level = "info";
        server = {
          host = "127.0.0.1";
          port = 8000;
        };
      };

      services.nginx.virtualHosts.${hostname} = {
        forceSSL = true;
        enableACME = true;
        locations."/".proxyPass = "http://127.0.0.1:8000";
      };

      preservation.preserveAt."/persist".directories = [ "/var/lib/readeck" ];
    };
}
