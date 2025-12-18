{
  nixosModule = { options, config, pkgs, lib, ... }:
    let
      vars = config.clan.core.vars.generators.mautrix-whatsapp.files;
    in
    {
      imports = [{
        config = lib.optionalAttrs (options ? clan) {
          clan.core.vars.generators.mautrix-whatsapp = {
            files.as-token = { };
            files.hs-token = { };
            files.env = { };
            runtimeInputs = [ pkgs.pwgen ];
            script = ''
              pwgen -s 64 1 | tr -d "\n" > $out/as-token
              pwgen -s 64 1 | tr -d "\n" > $out/hs-token
              echo "MAUTRIX_WHATSAPP_APPSERVICE_AS_TOKEN=$(cat $out/as-token)" > $out/env
              echo "MAUTRIX_WHATSAPP_APPSERVICE_HS_TOKEN=$(cat $out/hs-token)" >> $out/env
            '';
          };
        };
      }];

      services.mautrix-whatsapp.enable = true;

      services.mautrix-whatsapp.settings = {
        homeserver = {
          address = "https://matrix.enzim.ee";
          domain = "enzim.ee";
        };

        appservice = {
          # The bridge listens on all interfaces so it's reachable from the Matrix homeserver via Tailscale
          address = "http://gaia:29318";
          hostname = "0.0.0.0";
          port = 29318;
          database = {
            type = "sqlite3-fk-wal";
            uri = "file:/var/lib/mautrix-whatsapp/mautrix-whatsapp.db?_txlock=immediate";
          };
          id = "whatsapp";
          bot = {
            username = "whatsappbot";
            displayname = "WhatsApp Bridge Bot";
          };
          as_token = "$MAUTRIX_WHATSAPP_APPSERVICE_AS_TOKEN";
          hs_token = "$MAUTRIX_WHATSAPP_APPSERVICE_HS_TOKEN";
        };

        bridge = {
          username_template = "whatsapp_{{.}}";
          displayname_template = "{{or .BusinessName .PushName .JID}} (WA)";
          command_prefix = "!wa";
          permissions = {
            "*" = "relay";
            "enzim.ee" = "user";
            "@enzime:enzim.ee" = "admin";
          };
          relay = {
            enabled = true;
          };
        };

        logging = {
          min_level = "info";
          writers = [{
            type = "stdout";
            format = "pretty-colored";
          }];
        };
      };

      # Don't depend on local synapse since it runs on a different server
      services.mautrix-whatsapp.serviceDependencies = [ ];

      services.mautrix-whatsapp.environmentFile = vars.env.path;

      preservation.preserveAt."/persist".directories = [ "/var/lib/mautrix-whatsapp" ];

      # Generate appservice registration file for the Matrix homeserver
      # This file needs to be copied to the Matrix server and registered in its config
      environment.etc."mautrix-whatsapp/registration.yaml" = {
        text = ''
          id: whatsapp
          url: http://gaia:29318
          as_token: <read from ${vars.as-token.path}>
          hs_token: <read from ${vars.hs-token.path}>
          sender_localpart: whatsappbot
          namespaces:
            users:
              - regex: '@whatsapp_.*:enzim\.ee'
                exclusive: true
              - regex: '@whatsappbot:enzim\.ee'
                exclusive: true
          rate_limited: false
          de.sorunome.msc2409.push_ephemeral: true
          push_ephemeral: true
        '';
      };
    };
}
