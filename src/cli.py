"""CLI for HUD Affordable Housing Compliance Tracker."""

import click

from src.storage.database import get_connection, init_db, get_stats
from src.storage.database import upsert_lihtc, upsert_reac, upsert_multifamily


@click.group()
def cli():
    """HUD Affordable Housing Compliance Tracker CLI."""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Re-download even if cached")
def download(force):
    """Download raw data from HUD sources."""
    click.echo("Downloading LIHTC data...")
    from src.scrapers.lihtc import download_lihtc
    path = download_lihtc(force=force)
    click.echo(f"  LIHTC: {path}")

    click.echo("Downloading Multifamily Assisted Properties...")
    from src.scrapers.multifamily import download_multifamily_assisted
    path = download_multifamily_assisted(force=force)
    click.echo(f"  Multifamily Assisted: {path}")

    click.echo("Downloading HUD Insured Multifamily Properties...")
    from src.scrapers.multifamily import download_multifamily_insured
    path = download_multifamily_insured(force=force)
    click.echo(f"  Multifamily Insured: {path}")

    click.echo("Done.")


@cli.command()
def pipeline():
    """Run full ETL pipeline: parse, score, store, cross-link."""
    conn = get_connection()
    init_db(conn)

    # Parse LIHTC
    click.echo("Parsing LIHTC data...")
    from src.scrapers.lihtc import parse_lihtc, CACHE_FILE as LIHTC_FILE
    if LIHTC_FILE.exists():
        lihtc_records = parse_lihtc()
        click.echo(f"  Parsed {len(lihtc_records):,} LIHTC projects")

        # Score
        from src.validation.quality import score_lihtc
        for rec in lihtc_records:
            rec["quality_score"] = score_lihtc(rec)

        # Store
        n = upsert_lihtc(conn, lihtc_records)
        click.echo(f"  Stored {n:,} LIHTC projects")
    else:
        click.echo("  LIHTC data not found — run 'download' first")

    # Parse Multifamily Assisted
    click.echo("Parsing Multifamily Assisted Properties...")
    from src.scrapers.multifamily import (
        parse_multifamily_assisted, extract_reac_from_multifamily,
        parse_multifamily_insured,
    )
    from pathlib import Path
    mf_assisted_path = Path(__file__).parent.parent / "data" / "raw" / "multifamily_assisted.json"

    mf_records = []
    if mf_assisted_path.exists():
        mf_records = parse_multifamily_assisted(mf_assisted_path)
        click.echo(f"  Parsed {len(mf_records):,} assisted properties")

        # Score multifamily
        from src.validation.quality import score_multifamily
        for rec in mf_records:
            # Remove _ fields before scoring
            score_rec = {k: v for k, v in rec.items() if not k.startswith("_")}
            rec["quality_score"] = score_multifamily(score_rec)

        # Store multifamily (without _ fields)
        store_recs = [{k: v for k, v in r.items() if not k.startswith("_")} for r in mf_records]
        n = upsert_multifamily(conn, store_recs)
        click.echo(f"  Stored {n:,} multifamily properties")

        # Extract and store REAC inspections from multifamily data
        click.echo("Extracting REAC inspections from multifamily data...")
        reac_records = extract_reac_from_multifamily(mf_records)
        click.echo(f"  Extracted {len(reac_records):,} REAC inspections")

        from src.validation.quality import score_reac
        for rec in reac_records:
            rec["quality_score"] = score_reac(rec)

        n = upsert_reac(conn, reac_records)
        click.echo(f"  Stored {n:,} REAC inspections")
    else:
        click.echo("  Multifamily assisted data not found — run 'download' first")

    # Parse Multifamily Insured (merge into multifamily table)
    mf_insured_path = Path(__file__).parent.parent / "data" / "raw" / "multifamily_insured.json"
    if mf_insured_path.exists():
        insured_records = parse_multifamily_insured(mf_insured_path)
        click.echo(f"  Parsed {len(insured_records):,} insured properties")

        from src.validation.quality import score_multifamily
        for rec in insured_records:
            score_rec = {k: v for k, v in rec.items() if not k.startswith("_")}
            rec["quality_score"] = score_multifamily(score_rec)

        # Extract REAC from insured too
        insured_reac = extract_reac_from_multifamily(insured_records)
        if insured_reac:
            from src.validation.quality import score_reac
            for rec in insured_reac:
                rec["quality_score"] = score_reac(rec)
            n = upsert_reac(conn, insured_reac)
            click.echo(f"  Stored {n:,} additional REAC inspections from insured data")

        store_recs = [{k: v for k, v in r.items() if not k.startswith("_")} for r in insured_records]
        n = upsert_multifamily(conn, store_recs)
        click.echo(f"  Stored {n:,} insured properties")
    else:
        click.echo("  Multifamily insured data not found — run 'download' first")

    # Cross-link
    click.echo("Cross-linking records...")
    from src.normalization.cross_linker import cross_link_all
    link_stats = cross_link_all(conn)
    for key, val in link_stats.items():
        click.echo(f"  {key}: {val:,}")

    conn.close()
    click.echo("Pipeline complete.")


@cli.command()
def stats():
    """Show database statistics."""
    conn = get_connection()
    s = get_stats(conn)
    conn.close()

    click.echo("=== HUD Affordable Housing Compliance Tracker ===")
    click.echo(f"LIHTC Projects:        {s.get('lihtc_projects', 0):>10,}")
    click.echo(f"REAC Inspections:      {s.get('reac_inspections', 0):>10,}")
    click.echo(f"Section 8 Contracts:   {s.get('section8_contracts', 0):>10,}")
    click.echo(f"Multifamily Props:     {s.get('multifamily_properties', 0):>10,}")
    click.echo(f"Cross-Links:           {s.get('cross_links', 0):>10,}")
    click.echo(f"Owner Profiles:        {s.get('owners', 0):>10,}")
    click.echo(f"LIHTC States:          {s.get('lihtc_states', 0):>10}")
    click.echo(f"Total LIHTC Units:     {s.get('total_lihtc_units', 0):>10,}")
    click.echo(f"Avg Inspection Score:  {s.get('avg_inspection_score', 0):>10.1f}")
    click.echo(f"Failing Inspections:   {s.get('failing_inspections', 0):>10,}")


@cli.command()
@click.option("--format", "fmt", default="all", type=click.Choice(["csv", "json", "excel", "markdown", "all"]))
def export(fmt):
    """Export data in various formats."""
    conn = get_connection()
    from src.export.exporter import export_all
    results = export_all(conn, fmt=fmt)
    conn.close()

    for format_name, paths in results.items():
        if isinstance(paths, list):
            for p in paths:
                click.echo(f"  {format_name}: {p}")
        else:
            click.echo(f"  {format_name}: {paths}")

    click.echo("Export complete.")


@cli.command()
def dashboard():
    """Launch Streamlit dashboard."""
    import subprocess
    import sys
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "src/dashboard/app.py",
        "--server.headless", "true",
    ])


if __name__ == "__main__":
    cli()
