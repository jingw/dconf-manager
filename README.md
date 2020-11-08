dconf-manager
=============
Tool for managing GNOME dconf settings

This config says to purge everything in `/org/gnome/gedit` and add the given configuration.
```
$ cat dconf.ini
[org/gnome/gedit]
[org/gnome/gedit/preferences/editor]
auto-indent=true
bracket-matching=true
insert-spaces=true
tabs-size=uint32 4
wrap-mode='none'
```

```diff
$ ./dconf_manager.py dconf.ini
< org/gnome/gedit/plugins/active-plugins=['modelines', 'filebrowser', 'spell', 'docinfo', 'time']
> org/gnome/gedit/preferences/editor/auto-indent=true
> org/gnome/gedit/preferences/editor/bracket-matching=true
> org/gnome/gedit/preferences/editor/insert-spaces=true
> org/gnome/gedit/preferences/editor/tabs-size=uint32 4
> org/gnome/gedit/preferences/editor/wrap-mode='none'
< org/gnome/gedit/preferences/ui/show-tabs-mode='auto'
< org/gnome/gedit/state/window/bottom-panel-size=140
< org/gnome/gedit/state/window/side-panel-active-page='GeditWindowDocumentsPanel'
< org/gnome/gedit/state/window/side-panel-size=200
< org/gnome/gedit/state/window/size=(900, 700)
< org/gnome/gedit/state/window/state=128
```

By default, nothing is done. Pass `-a` / `--apply` to actually commit the changes to dconf.

See `--help` for more.

Development
===========

[![CI](https://github.com/jingw/shellquery/workflows/CI/badge.svg)](https://github.com/jingw/shellquery/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/jingw/dconf-manager/branch/master/graph/badge.svg)](https://codecov.io/gh/jingw/dconf-manager)

Python 3 is required.

```
pip install -r dev_requirements.txt
pytest
```
