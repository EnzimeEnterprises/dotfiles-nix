# Tailscale OIDC Workload Identity Federation
#
# This module enables Tailscale authentication via OIDC tokens instead of
# traditional auth keys. See: https://tailscale.com/kb/1581/workload-identity-federation
#
# Requirements:
# - Tailscale v1.90.1+
# - A workload identity credential configured in the Tailscale admin console
# - An OIDC identity provider (GitHub Actions, GCP, Azure, or custom)
#
# For machines without native OIDC (e.g., Vultr VPS), the token can be
# provided during deployment via a file or environment variable.
{
  nixosModule = { config, pkgs, lib, ... }:
    let
      cfg = config.services.tailscale.oidc;

      # Script to get the OIDC token from various sources
      getTokenScript = pkgs.writeShellScript "tailscale-get-oidc-token" ''
        set -euo pipefail

        # Priority 1: Token file (for deployment-time injection)
        ${lib.optionalString (cfg.tokenFile != null) ''
          if [ -f "${cfg.tokenFile}" ]; then
            cat "${cfg.tokenFile}"
            exit 0
          fi
        ''}

        # Priority 2: Environment variable
        if [ -n "''${TAILSCALE_OIDC_TOKEN:-}" ]; then
          echo "$TAILSCALE_OIDC_TOKEN"
          exit 0
        fi

        # Priority 3: Token command (for native OIDC environments)
        ${lib.optionalString (cfg.tokenCommand != []) ''
          ${lib.escapeShellArgs cfg.tokenCommand}
          exit 0
        ''}

        # Priority 4: GitHub Actions OIDC (if running in GHA)
        if [ -n "''${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ] && [ -n "''${ACTIONS_ID_TOKEN_REQUEST_URL:-}" ]; then
          ${lib.getExe pkgs.curl} -sS -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=${cfg.audience}" | \
            ${lib.getExe pkgs.jq} -r '.value'
          exit 0
        fi

        echo "No OIDC token source available" >&2
        exit 1
      '';
    in
    {
      options.services.tailscale.oidc = {
        enable = lib.mkEnableOption "Tailscale OIDC workload identity authentication";

        clientId = lib.mkOption {
          type = lib.types.str;
          default = "";
          description = ''
            The workload identity credential ID from the Tailscale admin console.
            This is NOT an OAuth client ID - it's specific to workload identity federation.
          '';
        };

        clientIdFile = lib.mkOption {
          type = lib.types.nullOr lib.types.path;
          default = null;
          description = ''
            Path to a file containing the workload identity credential ID.
            If set, this takes precedence over `clientId`.
          '';
        };

        audience = lib.mkOption {
          type = lib.types.str;
          default = "https://tailscale.com";
          description = ''
            The audience (aud claim) to request in the OIDC token.
            This should match what's configured in the Tailscale workload identity credential.
          '';
        };

        tokenFile = lib.mkOption {
          type = lib.types.nullOr lib.types.path;
          default = null;
          description = ''
            Path to a file containing the OIDC identity token.
            Useful for deployment scenarios where the token is injected at install time.
            The file can be deleted after initial authentication since state is preserved.
          '';
        };

        tokenCommand = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          default = [ ];
          description = ''
            Command to execute to obtain the OIDC identity token.
            The command should output just the JWT token to stdout.

            Examples:
            - For GCP: ["gcloud" "auth" "print-identity-token" "--audiences=https://tailscale.com"]
            - For Azure: Custom script using IMDS
          '';
        };

        tags = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          default = [ ];
          description = ''
            ACL tags to apply to the device. Must match the tags configured
            in the workload identity credential.
          '';
        };

        ephemeral = lib.mkOption {
          type = lib.types.bool;
          default = true;
          description = ''
            Whether to register the device as ephemeral.
            Ephemeral devices are automatically removed when they go offline.
          '';
        };

        preauthorized = lib.mkOption {
          type = lib.types.bool;
          default = false;
          description = ''
            Whether to preauthorize the device (skip admin approval).
          '';
        };
      };

      config = lib.mkIf cfg.enable {
        assertions = [
          {
            assertion = config.services.tailscale.enable;
            message = "services.tailscale.oidc requires services.tailscale.enable = true";
          }
          {
            assertion = cfg.clientIdFile != null || cfg.clientId != "";
            message = "Either services.tailscale.oidc.clientId or clientIdFile must be set";
          }
        ];

        # Ensure we don't use authKeyFile when OIDC is enabled
        services.tailscale.authKeyFile = lib.mkForce null;

        systemd.services.tailscale-oidc-auth = {
          description = "Tailscale OIDC Authentication";
          after = [ "network-online.target" "tailscaled.service" ];
          wants = [ "network-online.target" ];
          requires = [ "tailscaled.service" ];
          wantedBy = [ "multi-user.target" ];

          # Only run if not already authenticated
          unitConfig = {
            # Check for existing state - if present, tailscale should already be authenticated
            ConditionPathExists = "!/var/lib/tailscale/tailscaled.state";
          };

          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
            Restart = "on-failure";
            RestartSec = "10s";
            # Allow reading token file if specified
            ReadOnlyPaths = lib.optional (cfg.tokenFile != null) cfg.tokenFile;
          };

          path = [ config.services.tailscale.package pkgs.jq pkgs.curl ];

          script =
            let
              clientIdParam =
                if cfg.clientIdFile != null
                then ''$(cat "${cfg.clientIdFile}")''
                else cfg.clientId;

              # Build client-id with optional parameters
              # Format: client-id?ephemeral=false&preauthorized=true
              clientIdParams = lib.concatStringsSep "&" (
                lib.optional (!cfg.ephemeral) "ephemeral=false"
                ++ lib.optional cfg.preauthorized "preauthorized=true"
              );

              clientIdWithParams =
                if clientIdParams != ""
                then "${clientIdParam}?${clientIdParams}"
                else clientIdParam;

              tagsArg =
                if cfg.tags != [ ]
                then "--advertise-tags=${lib.concatStringsSep "," cfg.tags}"
                else "";
            in
            ''
              set -euo pipefail

              echo "Obtaining OIDC identity token..."
              ID_TOKEN=$(${getTokenScript})

              if [ -z "$ID_TOKEN" ]; then
                echo "Failed to obtain OIDC identity token"
                exit 1
              fi

              echo "Authenticating to Tailscale with OIDC workload identity..."
              CLIENT_ID="${clientIdWithParams}"
              tailscale up \
                --client-id="$CLIENT_ID" \
                --id-token="$ID_TOKEN" \
                ${tagsArg} \
                --reset

              echo "Tailscale OIDC authentication successful"

              # Clean up token file if it exists (one-time use)
              ${lib.optionalString (cfg.tokenFile != null) ''
                if [ -f "${cfg.tokenFile}" ]; then
                  rm -f "${cfg.tokenFile}" || true
                fi
              ''}
            '';
        };

        # Re-authentication service for when state is lost or connection drops
        systemd.services.tailscale-oidc-reauth = {
          description = "Tailscale OIDC Re-authentication";
          after = [ "network-online.target" "tailscaled.service" ];
          wants = [ "network-online.target" ];
          requires = [ "tailscaled.service" ];

          # Run periodically to ensure connectivity
          startAt = "hourly";

          serviceConfig = {
            Type = "oneshot";
            ReadOnlyPaths = lib.optional (cfg.tokenFile != null) cfg.tokenFile;
          };

          path = [ config.services.tailscale.package pkgs.jq pkgs.curl ];

          script =
            let
              clientIdParam =
                if cfg.clientIdFile != null
                then ''$(cat "${cfg.clientIdFile}")''
                else cfg.clientId;

              clientIdParams = lib.concatStringsSep "&" (
                lib.optional (!cfg.ephemeral) "ephemeral=false"
                ++ lib.optional cfg.preauthorized "preauthorized=true"
              );

              clientIdWithParams =
                if clientIdParams != ""
                then "${clientIdParam}?${clientIdParams}"
                else clientIdParam;

              tagsArg =
                if cfg.tags != [ ]
                then "--advertise-tags=${lib.concatStringsSep "," cfg.tags}"
                else "";
            in
            ''
              set -euo pipefail

              # Check if already connected
              STATUS=$(tailscale status --json 2>/dev/null | jq -r '.BackendState // "NoState"') || STATUS="Error"

              if [ "$STATUS" = "Running" ]; then
                echo "Tailscale already connected, skipping re-auth"
                exit 0
              fi

              echo "Tailscale not connected (status: $STATUS), attempting re-authentication..."

              # Try to get a token - this may fail if no token source is available
              if ! ID_TOKEN=$(${getTokenScript} 2>/dev/null); then
                echo "No OIDC token available for re-authentication"
                echo "Manual intervention may be required if tailscale disconnects"
                exit 0
              fi

              if [ -z "$ID_TOKEN" ]; then
                echo "Empty OIDC token, skipping re-auth"
                exit 0
              fi

              CLIENT_ID="${clientIdWithParams}"
              tailscale up \
                --client-id="$CLIENT_ID" \
                --id-token="$ID_TOKEN" \
                ${tagsArg}

              echo "Tailscale re-authentication successful"
            '';
        };
      };
    };
}
