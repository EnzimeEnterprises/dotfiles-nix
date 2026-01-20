{
  homeModule = { inputs, lib, pkgs, ... }: {
    home.packages = builtins.attrValues {
      inherit (inputs.llm-agents.packages.${pkgs.stdenv.hostPlatform.system})
        ccusage
        claude-code;
    };

    home.file.".claude/CLAUDE.md".source = ../files/CLAUDE.md;

    home.file.".claude/settings.json".text = lib.generators.toJSON { } {
      permissions = {
        allow = [ ];
        defaultMode = "default";
      };
      enabledPlugins = {
        "pyright-lsp@claude-plugins-official" = true;
        "clangd-lsp@claude-plugins-official" = true;
      };
      alwaysThinkingEnabled = true;
      cleanupPeriodDays = 99999;
      hooks = {
        Stop = [
          {
            matcher = "";
            hooks = [
              {
                type = "command";
                command = "jj --quiet status";
              }
            ];
          }
        ];
      };
      statusLine = {
        type = "command";
        command = lib.getExe inputs.llm-agents.packages.${pkgs.stdenv.hostPlatform.system}.ccstatusline;
        padding = 0;
      };
    };
  };
}
