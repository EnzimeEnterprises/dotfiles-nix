{
  imports = [ "acme" ];

  nixosModule = { options, config, pkgs, lib, ... }:
    let
      matrixDomain = "enzim.ee";
      matrixAddress = "https://matrix.enzim.ee";
    in {
      imports = [{
        config = lib.optionalAttrs (options ? clan) {
          clan.core.vars.generators.mautrix-meta-instagram = {
            files.as-token = { };
            files.hs-token = { };
            runtimeInputs = [ pkgs.pwgen ];
            script = ''
              pwgen -s 64 1 | tr -d "\n" > $out/as-token
              pwgen -s 64 1 | tr -d "\n" > $out/hs-token
            '';
          };
        };
      }];

      services.mautrix-meta.instances.instagram = {
        enable = true;

        settings = {
          homeserver = {
            domain = matrixDomain;
            address = matrixAddress;
          };

          appservice = {
            id = "instagram";
            bot.username = "instagrambot";
            # Use environment variable substitution for secrets
            as_token = "$AS_TOKEN";
            hs_token = "$HS_TOKEN";
          };

          meta.mode = "instagram";

          bridge = {
            # Allow the main user to use the bridge
            permissions = {
              "${matrixDomain}" = "user";
              "@enzime:${matrixDomain}" = "admin";
            };

            # Relay mode disabled by default
            relay.enabled = false;
          };

          encryption = {
            allow = true;
            default = true;
            require = false;
            appservice = false;
          };

          logging = {
            min_level = "info";
            writers = [{
              type = "stdout";
              format = "pretty-colored";
            }];
          };
        };

        environmentFile = "/run/mautrix-meta-instagram.env";
      };

      # Generate environment file with secrets before the bridge starts
      systemd.services.mautrix-meta-instagram-env = {
        description = "Generate mautrix-meta-instagram environment file";
        wantedBy = [ "mautrix-meta-instagram.service" ];
        before = [ "mautrix-meta-instagram.service" ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
        };
        script = ''
          cat > /run/mautrix-meta-instagram.env <<EOF
          AS_TOKEN=$(cat ${config.clan.core.vars.generators.mautrix-meta-instagram.files.as-token.path})
          HS_TOKEN=$(cat ${config.clan.core.vars.generators.mautrix-meta-instagram.files.hs-token.path})
          EOF
          chmod 600 /run/mautrix-meta-instagram.env
        '';
      };

      preservation.preserveAt."/persist".directories = [
        "/var/lib/mautrix-meta-instagram"
      ];

      # The registration file will be at:
      # /var/lib/mautrix-meta-instagram/meta-registration.yaml
      # This needs to be copied to the Matrix homeserver
    };
}
