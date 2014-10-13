katello-rapidnode
=================

To run:

1. `git clone` this repository
2. Update the following per your prefs:
	* `katello-rapidnode.ini`
	* `myrepofile.repo` (with any additional repos you want to install)
3. Execute `katello-rapidnode.py`


Code Contribution
-----------------

1. git clone this repo
2. Make necessary code changes
3. Run local tests and validate the code
4. Make sure pylint and flake8 pass

```sh
flake8 .
pylint *.py
```
