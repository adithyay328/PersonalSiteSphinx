# Docker file for the sphinx dev environment

# Sphinx has their own dev image, which ships with everything
# we need; just install stuff we need on top of that
FROM sphinxdoc/sphinx

# Installs python packages that we need
RUN pip3 install furo sphinx-design myst-parser sphinx-autobuild sphinx-sitemap

# Runs our make script, building site HTML
# CMD cd /app/site; while sleep 2; do make html; done
CMD rm -rf /app/site/build; cd /app/site; ls .; sphinx-autobuild source/ build/html