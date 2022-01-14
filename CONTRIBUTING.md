# Contributing to Variety

First off, thank you for helping!

## Bug tracking and bug fixing

Many of the reported bugs for Variety are about a problem happening in a particular
OS or desktop environment, under very particular conditions, or are more or less
impossible for us, the main developers, to reproduce.

Thus a pull request where the author has managed to reproduce reliably a bug and provides a fix
is an extremely valuable contribution - these are always very welcome.

## Translations

As of July 2021 we are using Transifex to sync up translations: https://www.transifex.com/variety/variety

Ping **@jlu5** if you have any issues with this - translation platforms are fairly new to us.

## Bigger changes or new features

If you plan on implementing any significant changes or developing new features,
please sync your intentions with the main developers, Peter Levi and James Lu ahead of time,
then open a PR early in the development phase.

## New image sources

If you plan on developing support for new image sources in Variety, please sync ahead of time
with Peter Levi.

Every new image source to be added to Variety should meet several criteria:

- The license of the images there must explicitly permit usage of the images as wallpapers
- The image source should provide some sort of an API or a structured feed (e.g., json or xml).
  Scraping data out of HTML is not acceptable for new sources in Variety.
- The image source must provide image author attribution
- Additionally, as a general rule we should try to select high-quality sources that make good
  wallpapers. The general policy is that we prefer quality over both quantity and searchability /
  customization.

Suggestions for adding specific Flickr photographers' feeds as default sources are also welcome, as
long as their images meet the license and quality criteria above (the other two are met
by default with Flickr)

## Code style

We use Black and isort, using line length of 100 symbols.
If you wish to contribute, please install Black and isort with `pip install black isort`.
Run on changed files with:

```
isort -rc edited_file_or_folder
black --line-length 100 --target-version py35 edited_file_or_folder
```

Or use directly the provided script `toolchain/autoformat` for this.
There are also configuraton files for both isort and black (`.isort.cfg` and `pyproject.toml`), so
just running `black` without passing in parameters will still use the correct settings.

There is also a pre-commit hook available that will do these steps for you, install it with

```
cd .git/hooks && ln -sf ../../toolchain/pre-commit-autoformat pre-commit
```

## Testing

We don't have CI support, yet. Please make sure all tests under the `tests` folder pass in your
branch. Run tests with, from the root of the project:

```
python3 -m unittest discover -p 'Test*.py' tests
```

All of the tests for the various image sources actually access the image source, so these
could fail sometimes when the remote site is down for maintenance - use common sense for whether
your changes caused the failure or it failed because of ax external reason.

Please note the test suite is not yet very extensive, and also does not cover any of the UI
aspects of Variety - always do some manual tests before you consider your PR is complete.
