# Cite Scholar

This is a little side project for getting citations easily from google scholar through the scholarly package.

## Usage

```
python -m citescholar [-t|--title] "<some title>" -c "<apa>"
```

Get the citation from a specific paper and cite in apa style. Use `-c` for specific citation style
default is _bibtex_.

```
python -m citescholar -t "<some title>" --no-save
```

Get the citation but don't save it in a sqlite3 database.

```
python -m citescholar -t "<some title>" [-s|--sqlite3] "<some db file name>"
```

## TODO

- [ ] add new citation styles by parsing the bibtex style
