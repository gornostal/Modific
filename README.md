Modific
=========

[![Join the chat at https://gitter.im/gornostal/Modific](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/gornostal/Modific?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Modific is a ST2(3) plugin for highlighting lines changed since the last commit (you know what I mean if you used Netbeans).

For now it supports **Git**, **SVN**, **Bazaar**, **Mercurial** and **TFS**.


Install
-------

The easiest way to install is through **[Package Control](http://wbond.net/sublime\_packages/package\_control)**.

Once you install Package Control, restart ST3 and bring up the Command Palette (`Ctrl+Shift+P` on Linux/Windows, `Cmd+Shift+P` on OS X). Select "Package Control: Install Package", wait while Package Control fetches the latest package list, then select *Modific* when the list appears. The advantage of using this method is that Package Control will automatically keep *Modific* up to date with the latest version.

Or you can **download** the latest source from [GitHub](https://github.com/gornostal/Modific/zipball/master) and copy the *Modific* folder to your Sublime Text "Packages" directory.

Or **clone** the repository to your Sublime Text "Packages" directory:

    git clone git://github.com/gornostal/Modific.git


The "Packages" directory is located at:

* OS X:

        ~/Library/Application Support/Sublime Text 3/Packages/

* Linux:

        ~/.config/sublime-text-2/Packages/

* Windows:

        %APPDATA%/Roaming/Sublime Text 3/Packages/

Please, make sure your VCS (version control system) binaries is in the PATH (**especially if you are on Windows**).

To do that on Windows, open `Control Panel -> System -> Advanced system settings -> Environment variables -> System Variables`, find PATH, click "Edit" and append `;C:\path\to\VCS\binaries` for every VCS you will use (or make sure it's already there).

Features / Usage
----------------

**Highlight changes** *(when file is saved)*
[![Highlight changes](http://i.imgur.com/DX8TeJTl.jpg)](http://i.imgur.com/DX8TeJT.jpg)

**Show diff** `Ctrl+Alt+D` on Linux/Windows and OS X
[![Show diff](http://i.imgur.com/csCw7l.jpg)](http://i.imgur.com/csCw7.jpg)

**Preview of the commited code for current line** `Ctrl+Alt+C` on Linux/Windows, `Ctrl+Super+C` on OS X
[![Preview](http://i.imgur.com/siVOXl.jpg)](http://i.imgur.com/siVOX.jpg)

**Revert modification** `Ctrl+Alt+R` on Linux/Windows, `Ctrl+Super+R` on OS X

This command reverts modifications if your cursor stays on modified line (or if on group of lines, then whole group will be reverted)

**View uncommitted files in a quick panel** `Ctrl+Alt+U` on Linux/Windows, `Ctrl+Super+U` on OS X
[![Preview](http://i.imgur.com/sldHNl.jpg)](http://i.imgur.com/sldHN.jpg)

**Go through changed lines** `Ctrl+Shift+Page Up(Down)`

For those who expected to see a clone of Netbeans feature - unfortunately, with existing Sublime Text API that is impossible :(

[Discussion on the forum](http://www.sublimetext.com/forum/viewtopic.php?f=5&t=7468)

**Toggle highlighting on/off** `Ctl+Shift+h, Ctrl+Shift+l`

Configuring
-----------

Open `Prefrences -> Package Settings -> Modific -> Settings - Default` and look for available settings.

If you want to change something, don't do it in this file. Open `Preferences -> Package Settings -> Modific -> Settings - User` and put there your configuration.

You can configure is a type of icon (dot, circle or bookmark) and path for your VCS binaries (or leave them as is, if you have them in your PATH). It's also possible to set priority for VCS used (when you have more than one simultaneously) by reordering their definitions.

If some sacred punishment has been bestowed upon you, and you have no other choice but to use OS, where console has non-UTF8 encoding, you can set console_encoding parameter to the name of your beloved encoding. This parameter is specifically designed for Windows XP users, who have their git repositories in folders with cyrillic path. Since russian XP uses CP1251 as default encoding (including console), VCS diff commands will be encoded appropriately, when using this parameter.

If you use different than the default theme, you can customize colors of bullets on the gutter by adding [this](https://gist.github.com/3692073) chunk of code to your theme.

### SVN users
If you are using SVN 1.7 you may want to turn on option `svn_use_internal_diff`.   
This instructs Subversion to use its built-in differencing engine
despite any external differencing mechanism that may be specified for use in the user's runtime configuration.

### Line endings
Modific takes into account `default_line_ending` setting that you can change in your "User Settings" (or per project/file basis).  
It determines what characters to use to join lines when Modific does "Revert change" action.  
Valid values: `system` (OS-dependent), `windows` (CRLF) and `unix` (LF).


Thanks to
---------

@beefsack for purchasing a license

License
-------
Released under the [WTFPLv2](http://sam.zoy.org/wtfpl/COPYING).
