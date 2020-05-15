# LSP-tagml
[TAGML](https://github.com/HuygensING/TAG/tree/master/TAGML) support for Sublime Text 3's LSP plugin.

Uses [TAGML Language Server](https://github.com/HuygensING/tagml-language-server) to provide completions, validation and other features for TAGML files. See linked repository for more information.
Depends on the [TAGML Sublime Syntax](https://github.com/HuygensING/tagml-sublime-syntax)

### Installation:

1. If you haven't already, install the [Sublime Syntax for TAGML](https://packagecontrol.io/packages/TAGML)
2. Install [LSP](https://packagecontrol.io/packages/LSP) and [LSP-tagml](https://packagecontrol.io/packages/LSP-tagml) from Package Control.
3. Wait for the language server binary download to complete.
4. Restart Sublime Text.


### Notes:

1. The TAGML Language Server requires the Java Runtime (JRE, >= 8) to be installed. To check that, run `java -version` in your login shell.
2. The plugin does not distribute, but downloads the `tagml-language-server-{version}.jar` binary from the official source.
