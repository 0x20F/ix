<h1 align="center">ix</h1>

<p align="center">(eeks) Simple dotfile pre-processor with a per-file configuration</p>


<br><br>


## Summary (TL;DR)
- `ix.py` is all you need
- config is an `ini` file.
- files to be processed must contain `#: ix-config` within the **first 20 lines**.
- more options can be specified per file after the `#: ix-config`.
- variables to be processed are defined as follows `#{{ section.variable }}`.
- default config directory `~/.config/ix/ixrc` (overwrite with `-c`)
- default parse directory `~/dots` (overwrite with `-d`)


<br><br>

## The Long Version
### What?
> **pre-processor**:
> a program that processes its input data to produce output that is used as input to another program.

This is a tool that allows you to define placeholders within your files (such as `${{ colors.background }}`) and then have them replaced with a value you've defined somewhere else whenever you please. Allowing you to stay worryless about where that value might be stored since you know it can only be stored in one place: `ixrc`.

<br><br><br>

### Why?
I've always had a lot of environment variables scattered all around the place. It's hard to keep track of everything in this way.

`ix` is an attempt at simplifying all of that by providing a single, central file that contains every single variable you might think of, or would need: `colors`, `paths`, `editor`, etc. All defined and controlled by you.

Aside from that, it also provides some nifty addons on top of the normal "find and replace" behaviour to allow you to customise exactly what happens to each file it reads, giving you even more control and structure.

<br><br><br>

### How does it work?
There's a total of **2** pieces to the puzzle:
1. The configuration that contains everything. By default `ix` will look for it in `~/.config/ix/ixrc` but can be easily overwritten with the `-c` flag.
2. The actual preprocessor script, the python file.

> When you run the script, it'll assume everything you want to parse is in `~/dots`, which is probably wrong so you'll want to overwrite that. You can do that with the `-d` flag and specifying a new path. 

`ix` will recursively read through the given directory and find any files that contain the `ix` declaration (which looks like this `#: ix-config`). Basically a comment followed by a colon. This `//:` works too, and this `/*:`, even this `--:`. If it doesn't work, then it can be added.
> Note that the definition needs to be within the **first 20 lines** of the file otherwise `ix` will ignore that file.

The lines after the definition can contain more information about how `ix` should handle this specific file. These are the simple addons I mentioned earlier. For example:
```bash
#: ix-config
#: to: /etc/whatever/

...
```
##### Check the full list of available options in the [documentation section](#documentation)

Here we tell `ix` to store the file inside `/etc/whatever` after it's been parsed, under the same name as the original file. Notice that the information related to `ix` is directly after the definition. This matters.

<br>

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
#: to: $HOME/.config/executable/executablerc

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

## Documentation
All available options for telling `ix` how to handle a specific file

<br>

#### `ix-config`
**The declaration** that turns a file into something that `ix` will process. It must show up within the first 20 lines of the file.

<br>

#### `prefix`
Custom symbol for the variable inclusion syntax.

> Note: This field (if used) needs to be the first thing in the configuration (after the declaration)

The default is `#` so variables are included like so `#{{ variable.name }}`

The prefix can be any symbol(s) you want, e.g:
```bash
#: ix-config
#: prefix: ¤

echo ¤{{ magical.variable }}
```

<br>

#### `to` | `out`
The output directory for the file.
> If the directory does not exist, it will be created before saving the file.

If not specified, the file will be added to the same directory as the original one, but with an `.ix` extension so it doesn't overwrite the original one (unlesss specified otherwise with the `as` key).
```bash
#: ix-config
#: to: /dev
```

<br>

#### `as` | `name`
The name of the processed file.
This is what the processed file will be saved as.

If not specified, the file will be saved under the same name.
```bash
#: ix-config
#: as: script.sh
```

<br>

#### `access`
Custom permissions to be set on the created file.

They will be set using python's `chmod` implementation so all numeric values will work. You can't do `+x` and the likes though, you'll have to do a numeric value.
```bash
#: ix-config
#: access: 777

echo "This file is executable"
```

<br>

#### All together now:
```bash
#: ix-config
#: prefix: ¤
#: to: $HOME/¤{{ user.images }}/
#: as: new_profile.png
```

<br><br>

### Misc
- `ix` variables can be used within the `ix` definitions as well, not just environment variables


<br><br>


### TODO
- More options for the `ix` configuration within each file
- Lockfile somewhere in `~/.cache` so the files don't get parsed multiple times without any changes.
