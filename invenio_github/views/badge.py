# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.


"""DOI Badge Blueprint."""

from __future__ import absolute_import

import os
import urllib

from flask import Blueprint, abort, current_app, make_response, redirect, \
    request, url_for

from ..api import GitHubAPI
from ..badge import create_badge

blueprint = Blueprint(
    'invenio_github_badge',
    __name__,
    url_prefix='/badge',
    static_folder='../static',
    template_folder='../templates',
)


def badge(doi, style=None):
    """Helper method to generate DOI badge."""
    doi_encoded = urllib.quote(doi, '')

    if style not in current_app.config['GITHUB_BADGE_STYLES']:
        style = current_app.config['GITHUB_BADGE_DEFAULT_STYLE']

    # Check if badge already exists
    badge_path = os.path.join(
        current_app.config['COLLECT_STATIC_ROOT'],
        'badges',
        '%s-%s.svg' % (doi_encoded, style)
    )

    if not os.path.exists(os.path.dirname(badge_path)):
        os.makedirs(os.path.dirname(badge_path))

    if not os.path.isfile(badge_path):
        try:
            create_badge('DOI', doi, 'blue', badge_path, style=style)
        except Exception:
            msg = '{0} is down.'.format(
                current_app.config['GITHUB_SHIELDSIO_BASE_URL']
            )
            current_app.logger.warning(msg, exc_info=True)
            return make_response(msg, 503)

    resp = make_response(open(badge_path, 'r').read())
    resp.content_type = 'image/svg+xml'
    return resp


#
# Views
#
@blueprint.route('/<int:user_id>/<path:repository>.svg', methods=['GET'])
def index(user_id, repository):
    """Generate a badge for a specific GitHub repository."""
    account = GitHubAPI(user_id=user_id)

    if repository not in account.extra_data['repos']:
        return abort(404)

    # Get the latest deposition
    try:
        dep = account.extra_data['repos'][repository]['depositions'][-1]
    except IndexError:
        return abort(404)

    # Extract DOI
    if 'doi' not in dep:
        return abort(404)

    doi = dep['doi']

    style = request.args.get('style', None)

    return badge(doi, style)


@blueprint.route('/<int:user_id>/<path:repository>.png', methods=['GET'])
def index_old(user_id, repository):
    """Legacy support for old badge icons."""
    style = request.args.get('style', None)
    full_url = url_for('.index', user_id=user_id,
                       repository=repository, style=style)
    return redirect(full_url)


@blueprint.route('/latestdoi/<int:user_id>/<path:repository>', methods=['GET'])
def latest_doi(user_id, repository):
    """Redirect to the newest record version."""
    account = GitHubAPI(user_id=user_id).account
    if account is None:
        return abort(404)

    # Get the latest deposition and extract doi
    try:
        dep = account.extra_data['repos'][repository]['depositions'][-1]
        doi = dep['doi']
    except (IndexError, KeyError):
        return abort(404)

    return redirect('http://dx.doi.org/{0}'.format(doi))
