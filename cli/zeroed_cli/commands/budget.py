"""
Budget management commands - zero-based budgeting.
"""

import click
from datetime import date
from rich.console import Console
from rich.table import Table

from ..core.database import get_session
from ..core.models import (
    CategoryGroup, Category, BudgetEntry, Transaction, Account
)
from ..services.budget_service import BudgetService

console = Console()


@click.group(name="budget")
def budget_group():
    """Manage monthly budgets."""
    pass


@budget_group.command()
@click.option("--month", "-m", help="Month (YYYY-MM), defaults to current")
def show(month):
    """Show budget for a month."""
    with get_session() as session:
        service = BudgetService(session)

        # Parse month or use current
        if month:
            try:
                year, mon = map(int, month.split("-"))
                target_date = date(year, mon, 1)
            except ValueError:
                console.print("[red]Invalid month format. Use YYYY-MM[/red]")
                return
        else:
            today = date.today()
            target_date = date(today.year, today.month, 1)

        budget_data = service.get_month_budget(target_date)

        # Header with key metrics
        console.print(f"\n[bold]Budget for {target_date.strftime('%B %Y')}[/bold]\n")

        # Ready to assign (available to budget)
        ready = budget_data["ready_to_assign"]
        if ready >= 0:
            console.print(f"Ready to Assign: [bold green]${ready:,.2f}[/bold green]")
        else:
            console.print(f"Ready to Assign: [bold red]${ready:,.2f}[/bold red] (overspent)")

        console.print()

        # Categories table
        table = Table(show_header=True)
        table.add_column("Category", min_width=25)
        table.add_column("Budgeted", justify="right", min_width=12)
        table.add_column("Activity", justify="right", min_width=12)
        table.add_column("Available", justify="right", min_width=12)

        for group in budget_data["groups"]:
            # Group header
            group_budgeted = sum(c["budgeted"] for c in group["categories"])
            group_activity = sum(c["activity"] for c in group["categories"])
            group_available = sum(c["available"] for c in group["categories"])

            table.add_row(
                f"[bold]{group['name']}[/bold]",
                f"[dim]${group_budgeted:,.2f}[/dim]",
                f"[dim]${group_activity:,.2f}[/dim]",
                f"[dim]${group_available:,.2f}[/dim]"
            )

            for cat in group["categories"]:
                available = cat["available"]
                if available < 0:
                    avail_str = f"[red]${available:,.2f}[/red]"
                elif available == 0:
                    avail_str = f"[dim]$0.00[/dim]"
                else:
                    avail_str = f"[green]${available:,.2f}[/green]"

                activity = cat["activity"]
                if activity < 0:
                    activity_str = f"[red]${activity:,.2f}[/red]"
                elif activity > 0:
                    activity_str = f"[green]+${activity:,.2f}[/green]"
                else:
                    activity_str = "[dim]$0.00[/dim]"

                table.add_row(
                    f"  {cat['name']}",
                    f"${cat['budgeted']:,.2f}",
                    activity_str,
                    avail_str
                )

        console.print(table)


@budget_group.command()
@click.argument("category")
@click.argument("amount", type=float)
@click.option("--month", "-m", help="Month (YYYY-MM), defaults to current")
def set(category, amount, month):
    """Set budget amount for a category."""
    with get_session() as session:
        service = BudgetService(session)

        # Parse month
        if month:
            try:
                year, mon = map(int, month.split("-"))
                target_date = date(year, mon, 1)
            except ValueError:
                console.print("[red]Invalid month format. Use YYYY-MM[/red]")
                return
        else:
            today = date.today()
            target_date = date(today.year, today.month, 1)

        try:
            service.set_category_budget(category, target_date, amount)
            session.commit()
            console.print(
                f"[green]Set {category} budget to ${amount:,.2f} "
                f"for {target_date.strftime('%B %Y')}[/green]"
            )
        except ValueError as e:
            console.print(f"[red]{e}[/red]")


@budget_group.command()
@click.option("--month", "-m", help="Month (YYYY-MM), defaults to current")
def auto(month):
    """Auto-budget based on average spending."""
    with get_session() as session:
        service = BudgetService(session)

        if month:
            try:
                year, mon = map(int, month.split("-"))
                target_date = date(year, mon, 1)
            except ValueError:
                console.print("[red]Invalid month format. Use YYYY-MM[/red]")
                return
        else:
            today = date.today()
            target_date = date(today.year, today.month, 1)

        suggestions = service.suggest_budgets(target_date)

        if not suggestions:
            console.print("[yellow]No spending history to base suggestions on[/yellow]")
            return

        table = Table(title="Budget Suggestions (3-month average)")
        table.add_column("Category")
        table.add_column("Suggested", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Difference", justify="right")

        for sug in suggestions:
            diff = sug["suggested"] - sug["current"]
            if diff > 0:
                diff_str = f"[green]+${diff:,.2f}[/green]"
            elif diff < 0:
                diff_str = f"[red]${diff:,.2f}[/red]"
            else:
                diff_str = "[dim]$0.00[/dim]"

            table.add_row(
                sug["category"],
                f"${sug['suggested']:,.2f}",
                f"${sug['current']:,.2f}",
                diff_str
            )

        console.print(table)

        if click.confirm("\nApply these suggestions?"):
            for sug in suggestions:
                service.set_category_budget(sug["category"], target_date, sug["suggested"])
            session.commit()
            console.print("[green]Budget updated![/green]")


@budget_group.command()
@click.option("--month", "-m", help="Month (YYYY-MM), defaults to current")
def summary(month):
    """Show budget summary."""
    with get_session() as session:
        service = BudgetService(session)

        if month:
            try:
                year, mon = map(int, month.split("-"))
                target_date = date(year, mon, 1)
            except ValueError:
                console.print("[red]Invalid month format. Use YYYY-MM[/red]")
                return
        else:
            today = date.today()
            target_date = date(today.year, today.month, 1)

        budget_data = service.get_month_budget(target_date)

        console.print(f"\n[bold]Budget Summary - {target_date.strftime('%B %Y')}[/bold]\n")

        # Calculate totals
        total_budgeted = sum(
            c["budgeted"]
            for g in budget_data["groups"]
            for c in g["categories"]
        )
        total_spent = abs(sum(
            c["activity"]
            for g in budget_data["groups"]
            for c in g["categories"]
            if c["activity"] < 0
        ))
        total_available = sum(
            c["available"]
            for g in budget_data["groups"]
            for c in g["categories"]
        )

        console.print(f"Ready to Assign:  ${budget_data['ready_to_assign']:>12,.2f}")
        console.print(f"Total Budgeted:   ${total_budgeted:>12,.2f}")
        console.print(f"Total Spent:      ${total_spent:>12,.2f}")
        console.print(f"Total Available:  ${total_available:>12,.2f}")

        # Count funded categories
        funded = sum(
            1
            for g in budget_data["groups"]
            for c in g["categories"]
            if c["budgeted"] > 0
        )
        total_cats = sum(len(g["categories"]) for g in budget_data["groups"])
        console.print(f"\nCategories Funded: {funded}/{total_cats}")

        # List overspent categories
        overspent = [
            (c["name"], c["available"])
            for g in budget_data["groups"]
            for c in g["categories"]
            if c["available"] < 0
        ]
        if overspent:
            console.print("\n[red]Overspent Categories:[/red]")
            for name, amount in overspent:
                console.print(f"  {name}: [red]${amount:,.2f}[/red]")
