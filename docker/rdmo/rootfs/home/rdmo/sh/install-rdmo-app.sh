#!/bin/bash

if [[ ! -d "${RDMO_APP}" ]]; then
  echo "Install RDMO App"
  git clone "${RDMO_APP_REPO}" "${RDMO_APP}"

  targ="${RDMO_APP}/config/settings/local.py"
  if [[ ! -f "${targ}" ]]; then
    cp -f /conf/template_local.py "${targ}"
  fi

fi

# Unlike local.py, which is a starting point the operator owns and edits,
# oidc.py is code that belongs to the image and is referenced by import path
# from the settings (ACCOUNT_ADAPTER). Refresh it on every start so it cannot
# drift away from the image it is supposed to match.
cp -f /conf/oidc.py "${RDMO_APP}/config/oidc.py"

# Same reasoning for the theme app that overrides the oidc login button.
rm -rf "${RDMO_APP}/rdmo_oidc_theme/templates"
cp -rf /conf/rdmo_oidc_theme "${RDMO_APP}/"

# The button image itself is operator supplied and therefore NOT part of the
# image: OIDC_CLIENT_LINKIMAGE points at a file, which is staged into the theme
# app's static folder so that the collectstatic below publishes it under
# /static/. Paths are resolved inside the container, where the host's VOLDIR is
# mounted at /vol - so "vol/logo.svg" and "/vol/logo.svg" both work.
theme_static="${RDMO_APP}/rdmo_oidc_theme/static/rdmo_oidc_theme"
rm -rf "${theme_static}"
mkdir -p "${theme_static}"
if [[ -n "${OIDC_CLIENT_LINKIMAGE}" ]]; then
  linkimage="/${OIDC_CLIENT_LINKIMAGE#/}"
  if [[ -f "${linkimage}" ]]; then
    echo "Using ${linkimage} as the oidc login button image"
    cp -f "${linkimage}" "${theme_static}/"
  else
    echo "WARNING: OIDC_CLIENT_LINKIMAGE is set but ${linkimage} does not exist," \
         "falling back to rdmo's built in provider logo"
  fi
fi

cd "${RDMO_APP}" && {
  python manage.py migrate
  #python manage.py download_vendor_files
  python manage.py collectstatic --no-input
  python manage.py setup_groups
}
