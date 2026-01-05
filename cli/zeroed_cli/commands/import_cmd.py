"""
CSV import commands.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from ..core.database import get_session
from ..core.models import Account, Transaction
from ..importers import get_importer, detect_format, list_importers
from ..categorization.engine import CategorizationEngine

console = Console()


@click.group(name="import")
def import_group():
    """Import transactions from CSV files."""
    pass


@import_group.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--account", "-a", required=True, help="Target account name")
@click.option("--format", "-f", "fmt", help="CSV format (chase, amex, generic)")
@click.option("--dry-run", is_flag=True, help="Preview without importing")
def csv(file, account, fmt, dry_run):
    """Import transactions from a CSV file."""
    filepath = Path(file)

    with get_session() as session:
        # Find account
        acc = session.query(Account).filter(Account.name.ilike(f"%{account}%")).first()
        if not acc:
            console.print(f"[red]Account '{account}' not found[/red]")
            console.print("Available accounts:")
            for a in session.query(Account).filter(Account.is_closed == False).all():
                console.print(f"  - {a.name}")
            return

        # Auto-detect format if not specified
        if not fmt:
            fmt = detect_format(filepath)
            if fmt:
                console.print(f"[blue]Auto-detected format: {fmt}[/blue]")
            else:
                console.print("[yellow]Could not auto-detect format, using 'generic'[/yellow]")
                fmt = "generic"

        # Get importer
        try:
            importer = get_importer(fmt)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            return

        # Parse CSV
        console.print(f"Parsing {filepath.name}...")
        try:
            transactions = importer.parse(filepath, acc.id)
        except Exception as e:
            console.print(f"[red]Error parsing CSV: {e}[/red]")
            return

        console.print(f"[green]Parsed {len(transactions)} transactions[/green]")

        if not transactions:
            console.print("[yellow]No transactions found in file[/yellow]")
            return

        # Show preview
        table = Table(title="Import Preview (first 10)")
        table.add_column("Date")
        table.add_column("Payee")
        table.add_column("Amount", justify="right")
        table.add_column("Memo")

        for txn in transactions[:10]:
            amount_str = f"${abs(txn.amount):,.2f}"
            if txn.amount < 0:
                amount_str = f"[red]-{amount_str}[/red]"
            else:
                amount_str = f"[green]+{amount_str}[/green]"
            table.add_row(
                txn.date.strftime("%Y-%m-%d"),
                (txn.raw_payee_name or "")[:30],
                amount_str,
                (txn.memo or "")[:30]
            )

        console.print(table)

        if len(transactions) > 10:
            console.print(f"[dim]... and {len(transactions) - 10} more[/dim]")

        if dry_run:
            console.print("\n[yellow]Dry run - no changes made[/yellow]")
            return

        # Import with categorization
        engine = CategorizationEngine(session)

        imported = 0
        skipped = 0
        categorized = 0

        with Progress() as progress:
            task = progress.add_task("Importing...", total=len(transactions))

            for txn in transactions:
                # Check for duplicates via import_id
                if txn.import_id:
                    existing = (
                        session.query(Transaction)
                        .filter(Transaction.import_id == txn.import_id)
                        .first()
                    )
                    if existing:
                        skipped += 1
                        progress.update(task, advance=1)
                        continue

                # Auto-categorize
                category = engine.categorize(txn.raw_payee_name)
                if category:
                    txn.category_id = category.id
                    categorized += 1

                session.add(txn)
                imported += 1
                progress.update(task, advance=1)

            # Update account balance
            total_imported = sum(
                t.amount for t in transactions
                if not session.query(Transaction)
                .filter(Transaction.import_id == t.import_id)
                .first()
            )
            acc.current_balance += total_imported

            session.commit()

        console.print(f"\n[bold green]Imported {imported} transactions[/bold green]")
        if skipped:
            console.print(f"[yellow]Skipped {skipped} duplicates[/yellow]")
        if categorized:
            console.print(f"[blue]Auto-categorized {categorized} transactions[/blue]")

        uncategorized = imported - categorized
        if uncategorized > 0:
            console.print(
                f"[dim]{uncategorized} transactions need categorization. "
                f"Run 'zeroed transactions list --uncategorized'[/dim]"
            )


@import_group.command()
def profiles():
    """List available import profiles/formats."""
    importers = list_importers()

    table = Table(title="Import Profiles")
    table.add_column("Name")
    table.add_column("Institution")
    table.add_column("Description")

    for imp in importers:
        table.add_row(imp["name"], imp["institution"], imp["description"])

    console.print(table)
    console.print("\n[dim]Use --format <name> to specify a format when importing[/dim]")
