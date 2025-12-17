{ config, self', inputs', lib, ... }:

let clan = inputs'.clan-core.packages.clan-cli;
in {
  terraform.backend.s3 = {
    endpoints.s3 = "https://s3.us-west-001.backblazeb2.com";
    bucket = "enzime-dotfiles-tf-state";
    key = "tofu.tfstate";
    region = "us-west-001";

    skip_credentials_validation = true;
    skip_region_validation = true;
    skip_metadata_api_check = true;
    skip_requesting_account_id = true;
    skip_s3_checksum = true;

    skip_bucket_root_access = true;
    skip_bucket_enforced_tls = true;
  };

  terraform.encryption = {
    key_provider.external.passphrase = {
      command = [ (lib.getExe self'.packages.provide-tf-passphrase) ];
    };

    key_provider.pbkdf2.state_encryption_password = {
      chain = lib.tf.ref "key_provider.external.passphrase";
    };

    method.aes_gcm.encryption_method.keys =
      lib.tf.ref "key_provider.pbkdf2.state_encryption_password";

    state.enforced = true;
    state.method = "method.aes_gcm.encryption_method";

    plan.enforced = true;
    plan.method = "method.aes_gcm.encryption_method";
  };

  terraform.required_providers.local.source = "hashicorp/local";
  terraform.required_providers.tailscale.source = "tailscale/tailscale";
  terraform.required_providers.tls.source = "hashicorp/tls";

  data.external.tailscale-api-key = {
    program =
      [ (lib.getExe self'.packages.get-clan-secret) "tailscale-api-key" ];
  };

  provider.tailscale.api_key =
    config.data.external.tailscale-api-key "result.secret";

  # NOTE: Tailscale authentication is now handled via OIDC workload identity federation
  # instead of auth keys. The workload identity credential must be created manually
  # in the Tailscale admin console:
  #
  # 1. Go to https://login.tailscale.com/admin/settings/trust-credentials
  # 2. Click "Credential" -> "OpenID Connect"
  # 3. Configure the OIDC issuer (GitHub Actions recommended for deployments)
  # 4. Set the subject claim pattern to match your deployment environment
  # 5. Copy the Client ID and run:
  #    clan vars set <hostname> tailscale-oidc/client-id
  #
  # See: https://tailscale.com/kb/1581/workload-identity-federation

  resource.tls_private_key.ssh_deploy_key = { algorithm = "ED25519"; };

  resource.local_sensitive_file.ssh_deploy_key = {
    filename = "${lib.tf.ref "path.module"}/.terraform-deploy-key";
    file_permission = "600";
    content =
      config.resource.tls_private_key.ssh_deploy_key "private_key_openssh";
  };
}
