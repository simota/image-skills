<!-- image:guidance -->
# Naming files

A name is the only thing about an image most people will ever read. It has to
survive a second version, a second size, a second format, and a reader who was
not there.

## Match what is already there

Open the directory the file is going into and read the existing names first.
Whatever they do — kebab case, a size suffix, a directory per surface — do that.
**A better convention introduced beside an existing one is two conventions**,
and every future reader now checks both.

Where nothing exists, pick one, write it down, and say plainly that it is now
the precedent.

## What a name has to carry

In this order, and only what is needed:

1. **What it is** — `landing-header`, not `image1`, not `final`
2. **Which variant**, if there is more than one — `landing-header-dark`
3. **Which size**, when several ship — as a suffix the build understands
4. **Which version**, when one is replaced rather than edited — a monotonic
   suffix, never `-final`, `-final2`, `-real-final`

```
landing-header.png              the source, full size
landing-header@2x.png           a density variant
landing-header-dark@2x.png      a theme variant of the same picture
landing-header-v2.png           a different picture that replaced the first
```

## Version suffix, not overwrite

The default is to write a sibling and let a person retire the old file. An
overwritten asset is a change nobody can review and nobody can undo, and it
silently changes every surface that referenced it — including the ones nobody
remembers.

Overwriting is a decision the human makes, in words, in advance.

## Names that cause trouble

- **Spaces and non-ASCII characters.** They survive a repository and break
  somewhere later
- **Upper case**, on a project whose other files are lower. Case-insensitive
  filesystems hide this locally and CI finds it
- **A date in the name.** It says when, which nobody needs, and hides which,
  which everybody does
- **`final`, `new`, `latest`, `copy`.** Each is true for about a day
- **A name describing the prompt.** The recipe holds the prompt; the name holds
  the job

## After renaming or adding

Follow every reference. A file added to a directory is not delivered until the
markup, the stylesheet, the manifest, or the document that consumes it points
at it — and that pointer was opened and checked, not assumed.
