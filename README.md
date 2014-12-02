katello-rapidnode
=================

Prerequisites:
-------------

1. Satellite 6 installed with no errors.
2. RH Subscription imported.
3. Required Repositories enabled. The following are mandatory:
	* Server rpms - rhel 6 or 7
	* RH Satellite 6 rpms - rhel 6 or 7
4. Enabled repositories are synced.
5. At least one life cycle environment created.
6. At least one content view created.
7. The content view is promoted to appropriate environments.


To run:
------

1. `git clone` this repository.
2. Copy `katello_rapidnode.sample.ini` and name it `katello_rapidnode.ini`.
   Update required parameters as necessary.
3. Copy `myrepofile.sample.repo` and name it `myrepofile.repo`.  Update with
   any additional repos you want to install.
4. Execute `katello-rapidnode.py`.


Code Contribution
-----------------

1. git clone this repo.
2. Make necessary code changes.
3. Run local tests and validate the code.
4. Make sure pylint and flake8 pass.

```sh
pip install --requirement requirements-optional.txt
flake8 .
pylint *.py
```
