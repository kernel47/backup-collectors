"""Route validated requests to the resource entrypoint."""

from core.models import CollectionReport


def execute(context, settings=None):
    if context.scope != "netbackup":
        report = CollectionReport.from_context(context)
        report.add_error(
            "configuration", "unsupported_scope", f"Scope {context.scope} is not implemented yet"
        )
        return report
    from collectors import netbackup

    collect = {
        "jobs": netbackup.collect_jobs,
        "policies": netbackup.collect_policies,
        "images": netbackup.collect_images,
        "slps": netbackup.collect_slps,
        "images-contents": netbackup.collect_images_contents,
    }[context.type]
    return collect(context, settings)
