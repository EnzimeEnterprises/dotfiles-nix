{
  imports = [ "acme" ];

  nixosModule = { options, config, pkgs, lib, ... }:
    let hostname = "vikunja.enzim.ee";
    in {
      imports = [{
        config = lib.optionalAttrs (options ? clan) {
          clan.core.vars.generators.vikunja = {
            files.jwt-secret = { };
            runtimeInputs = [ pkgs.coreutils pkgs.xkcdpass ];
            script = ''
              xkcdpass --numwords 6 --random-delimiters --valid-delimiters='1234567890!@#$%^&*()-_+=,.<>/?' --case random | tr -d "\n" > $out/jwt-secret
            '';
          };
        };
      }];

      services.vikunja.enable = true;
      services.vikunja.frontendScheme = "https";
      services.vikunja.frontendHostname = hostname;

      services.vikunja.environmentFiles = [
        config.clan.core.vars.generators.vikunja.files.jwt-secret.path
      ];

      services.vikunja.settings = {
        service = {
          enableregistration = false;
        };
      };

      services.nginx.virtualHosts.${hostname} = {
        forceSSL = true;
        enableACME = true;
      };

      preservation.preserveAt."/persist".directories = [ "/var/lib/vikunja" ];
    };
}
