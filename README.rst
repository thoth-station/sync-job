Thoth's one-time sync job
-------------------------

A job that syncs all the Thoth data to Thoth's knowledge graph.


Running the job
===============


.. code-block:: console

  oc process \
    -p DEADLINE_SECONDS="21600"
    -p IMAGE_VERSION="latest" \
    -p THOTH_SYNC_FORCE="0" \
    -p THOTH_SYNC_GRACEFUL="0" \
    -p THOTH_SYNC_DEBUG="0" \
  -f openshift.yaml | oc apply -f -

Cleaning objects
================

.. code-block:: console

  oc delete job -l component=sync
