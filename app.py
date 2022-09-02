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
import os

from typing import Optional

import click
from thoth.storages.sync import HANDLERS_MAPPING
from thoth.common import init_logging
from thoth.storages import GraphDatabase
from thoth.storages import __version__ as __thoth_storages_version__

from prometheus_client import CollectorRegistry, Gauge, Counter, push_to_gateway

prometheus_registry = CollectorRegistry()

__version__ = "0.2.5"
__component_version__ = f"{__version__}+ storages{__thoth_storages_version__}"

init_logging()
_LOGGER = logging.getLogger("thoth.sync")

# Metrics Data sync
_METRIC_INFO = Gauge(
    "thoth_data_sync_job_info",
    "Thoth Data Sync Job information",
    ["env", "version"],
    registry=prometheus_registry,
)

_METRIC_DOCUMENTS_SYNC_NUMBER = Counter(
    "thoth_data_sync_job",
    "Thoth Data Sync Job number of synced data per status",
    ["sync_type", "env", "version", "document_type"],
    registry=prometheus_registry,
)

_THOTH_DEPLOYMENT_NAME = os.environ["THOTH_DEPLOYMENT_NAME"]
_THOTH_METRICS_PUSHGATEWAY_URL = os.getenv("PROMETHEUS_PUSHGATEWAY_URL")
_METRIC_INFO.labels(_THOTH_DEPLOYMENT_NAME, __component_version__).inc()


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
        to_sync = {document_type: HANDLERS_MAPPING[document_type]}
    else:
        to_sync = HANDLERS_MAPPING

    for category, function in to_sync.items():

        stats = function(force=force_sync, graceful=graceful, graph=graph)

        _LOGGER.info(
            "Syncing triggered for %r documents completed with "
            "%d processed, %d synced, %d skipped and %d failed documents",
            category,
            *stats,
        )
        for amount, result in zip(stats[1:], ["synced", "skipped", "failed"]):
            _METRIC_DOCUMENTS_SYNC_NUMBER.labels(
                sync_type=result, env=_THOTH_DEPLOYMENT_NAME, version=__component_version__, document_type=category
            ).inc(amount)

    if _THOTH_METRICS_PUSHGATEWAY_URL:
        _LOGGER.debug(f"Submitting metrics to Prometheus pushgateway {_THOTH_METRICS_PUSHGATEWAY_URL}")
        push_to_gateway(
            _THOTH_METRICS_PUSHGATEWAY_URL,
            job="document-sync-job",
            registry=prometheus_registry,
        )


__name__ == "__main__" and sync()
