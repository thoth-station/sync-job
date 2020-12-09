#!/usr/bin/env python3
# thoth-sync
# Copyright(C) 2010 Red Hat, Inc.
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Sync Thoth documents to Thoth's knowledge graph."""

import logging

from typing import Optional

import click
import thoth.storages.sync as thoth_sync_module
from thoth.storages.sync import HANDLERS_MAPPING
from thoth.storages.sync import sync_solver_documents
from thoth.common import init_logging
from thoth.storages import GraphDatabase
from thoth.storages import __version__ as __thoth_storages_version__

__version__ = "0.2.1"
__component_version__ = f"{__version__}+ storages{__thoth_storages_version__}"

init_logging()
_LOGGER = logging.getLogger("thoth.sync")


@click.command()
@click.option("--force-sync", is_flag=True, help="Perform force sync of documents.", envvar="THOTH_SYNC_FORCE_SYNC")
@click.option("--graceful", is_flag=True, help="Continue on any error during the sync.", envvar="THOTH_SYNC_GRACEFUL")
@click.option("--debug", is_flag=True, help="Run in a debug mode", envvar="THOTH_SYNC_DEBUG")
@click.option(
    "--document-type",
    help="Thoth document type to be synced.",
    envvar="THOTH_DOCUMENT_TYPE",
    type=click.Choice(list(HANDLERS_MAPPING.keys()), case_sensitive=False),
)
def sync(force_sync: bool, graceful: bool, debug: bool, document_type: Optional[str]) -> None:
    """Sync Thoth data to Thoth's knowledge base."""
    if debug:
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.debug("Debug mode is on.")

    _LOGGER.info("Running syncing job in version %r", __component_version__)

    graph = GraphDatabase()
    graph.connect()

    if document_type:
        # We sync only a specific category of Thoth documents
        function = HANDLERS_MAPPING[document_type]
        stats = function(force=force_sync, graceful=graceful, graph=graph)

        _LOGGER.info(
            "Syncing triggered for %r function completed with "
            "%d processed, %d synced, %d skipped and %d failed documents",
            document_type,
            *stats,
        )
        return

    # First we need tosync solvers

    stats = sync_solver_documents(force=force_sync, graceful=graceful, graph=graph)

    _LOGGER.info(
        "Syncing triggered by sync_solver_documents function completed with "
        "%d processed, %d synced, %d skipped and %d failed documents",
        *stats,
    )

    for obj_name, function in thoth_sync_module.__dict__.items():
        if not obj_name.startswith("sync_"):
            _LOGGER.debug("Skipping attribute %r of thoth-storages syncing module: not a syncing function", obj_name)
            continue

        if obj_name == "sync_solver_documents":
            _LOGGER.debug("Skipping attribute %r of thoth-storages syncing module: solver already synced", obj_name)
            continue

        stats = function(force=force_sync, graceful=graceful, graph=graph)

        _LOGGER.info(
            "Syncing triggered by %r function completed with "
            "%d processed, %d synced, %d skipped and %d failed documents",
            obj_name,
            *stats,
        )


__name__ == "__main__" and sync()
