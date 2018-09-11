# machinic-bespoke

_prototypes, proofs of concept_

## Installation

Pip:

```
pip3 install git+https://github.com/galencm/machinic-bespoke --user --process-dependency-links
```

Develop while using pip:

```
git clone https://github.com/galencm/machinic-bespoke
cd machinic-bespoke/
pip3 install --editable ./ --user --process-dependency-links
```

Setup linting and formatting git commit hooks:

```
cd machinic-bespoke/
pre-commit install
pre-commit install -t commit-msg
```

## Usage

create a three frame animated gif from items sequenced with fold-ui (requires [gifsicle](http://www.lcdf.org/gifsicle/)):

```
 bespoke-animate foo.gif --animate-frame-start 0 --animate-frame-end 3
```

## Contributing
This project uses the C4 process 

[https://rfc.zeromq.org/spec:42/C4/](https://rfc.zeromq.org/spec:42/C4/
)

## License
Mozilla Public License, v. 2.0

[http://mozilla.org/MPL/2.0/](http://mozilla.org/MPL/2.0/)

