<h1 align="center">ix</h1>

<p align="center">(eeks) Simple dotfile preprocessor</p>


<br><br>


## Summary (TL;DR)
- `ix.py` is all you need
- config is an `ini` file.
- files to be processed must contain `#: ix-config` within the **first 20 lines**.
- more options can be specified per file after the `#: ix-config`.
- variables to be processed are defined as follows `#{{ section.variable }}`.
- default config directory `~/.config/ix/ixrc`.
- default parse directory `~/dots`.


<br><br>

## The Long Version
### Why?
I've always had a lot of variables defined in several different places. Some in `.profile` because something couldn't read `.zprofile`, some in `.zshrc` that I've completely forgot about but started using everywhere, and so on. Eventually, the bowl of spaghetti gets bigger and bigger. Everything running bash scripts was already a big enough mess. It's hard to keep track of everything. `.Xresources` defines some colors, but some configs can't use variables from `.Xresources` so you gotta redefine those colors in yet another place and it just gets messier and messier.

`ix` is an attempt at simplifying all of that by providing:
1. A single, central file that contains every single variable you might think of, or would need: `colors`, `paths`, `editor`, etc. All defined and controlled by you.
2. A simple toolkit to be used within each file that needs processing to allow `ix` to move it around, or rename it, or send it to some server, whatever.

<br><br><br>

### How does it work?
There's a total of **2** pieces to the puzzle:
1. The configuration that contains everything. By default `ix` will look for it in `~/.config/ix/ixrc` but can be easily overwritten with the `-c` flag.
2. The actual preprocessor script, the python file.

When you run the script, it'll assume everything you want to parse is in `~/dots`, which is probably wrong so you'll want to overwrite that. You can do that with the `-d` flag and specifying a new path. 

As it gets going, it'll loop through every file in the given directory and see if any of them has an `ix` definition within it.

A definition looks like this `#: ix-config`. Basically a comment followed by a colon. This `//:` works too, and this `/*:`, even this `--:`. It's an ever growing list basically. These are comments for different file types so the list can be expanded easily.

In order for the file to be parsed by `ix`, that definition needs to be within the **first 20 lines** of the file otherwise it'll ignore the file.
As soon as it finds that definition, it'll mark the file as something to parse and keep on reading.

The lines after the definition can contain more information about how `ix` should handle this specific file. For example:
```bash
#: ix-config
#: out: /etc/whatever/file.txt

...
```
The above example defines where the processed file should be stored. If this is not specified, it'll be stored in the same directory as the original file, under the same name, but with a `.ix` extension added so it doesn't overwrite the original file. Notice that the information related to `ix` is directly after the definition (no empty lines) and start with the same characters as the definition (`#:` in this case).

So that tells `ix` how to handle this specific file and do other magical things with it. The next thing we might want to do is tell it to add some custom variables lower down in the file.

#### Concrete example
Assume we have a configuration that looks like this:
```ini
[colors]
blue = blue
red = green
```
We might then have a bash script that executes something and we want those colors to be given as parameters. Something like this:
```bash
#!/usr/bin/env bash
# magic.sh


#: ix-config
#: out: $HOME/.config/executable/executablerc

# ...

executable --color #{{ colors.blue }} # and so on...
# ...
```
Now when we run `ix`, it'll see that the `magic.sh` file is something that needs parsing, it'll make sure to replace everything within the `#{{ }}` characters with the value defined in the configuration, giving us the following file:
```bash
#!/usr/bin/env bash
# magic.sh

# ...

executable --color blue # and so on...
#...
```
> Notice that it got rid of the `ix` definitions as well.

<br><br>

### Misc
- `ix` variables can be used within the `ix` definitions as well, not just environment variables


<br><br>


### TODO
- Custom variable inclusion symbol (so that you can define multiple options in case `#` doesn't look good before `{{`)
- More options for the `ix` configuration within each file
- Prettier terminal output (colors and things)