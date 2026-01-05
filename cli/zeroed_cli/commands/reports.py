"""
Spending reports commands.
"""

import click
from datetime import date
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from sqlalchemy import func

from ..core.database import get_session
from ..core.models import Transaction, Category, CategoryGroup, Account

console = Console()


@click.group(name="reports")
def reports_group():
    """Generate spending reports."""
    pass


@reports_group.command()
@click.option("--months", "-m", type=int, default=1, help="Number of months to include")
@click.option("--group", "-g", is_flag=True, help="Group by category group")
def spending(months, group):
    """Show spending by category."""
    with get_session() as session:
        today = date.today()
        start_date = date(today.year, today.month, 1)

        # Go back N months
        for _ in range(months - 1):
            if start_date.month == 1:
                start_date = date(start_date.year - 1, 12, 1)
            else:
                start_date = date(start_date.year, start_date.month - 1, 1)

        # Query spending by category
        results = (
            session.query(
                Category.name,
                CategoryGroup.name,
                func.sum(Transaction.amount)
            )
            .join(Category, Transaction.category_id == Category.id)
            .join(CategoryGroup, Category.group_id == CategoryGroup.id)
            .filter(Transaction.amount < 0)  # Only outflows
            .filter(Transaction.date >= start_date)
            .group_by(Category.id)
            .order_by(func.sum(Transaction.amount))
            .all()
        )

        if not results:
            console.print("[yellow]No spending data found[/yellow]")
            return

        if group:
            # Group by category group
            by_group = defaultdict(float)
            for cat_name, group_name, amount in results:
                by_group[group_name] += abs(amount)

            table = Table(title=f"Spending by Group ({months} month{'s' if months > 1 else ''})")
            table.add_column("Group")
            table.add_column("Amount", justify="right")
            table.add_column("% of Total", justify="right")

            total = sum(by_group.values())
            for group_name, amount in sorted(by_group.items(), key=lambda x: -x[1]):
                pct = (amount / total * 100) if total > 0 else 0
                table.add_row(
                    group_name,
                    f"${amount:,.2f}",
                    f"{pct:.1f}%"
                )

            table.add_row("", "", "")
            table.add_row("[bold]Total[/bold]", f"[bold]${total:,.2f}[/bold]", "100%")
        else:
            table = Table(title=f"Spending by Category ({months} month{'s' if months > 1 else ''})")
            table.add_column("Category")
            table.add_column("Group")
            table.add_column("Amount", justify="right")
            table.add_column("% of Total", justify="right")

            total = sum(abs(r[2]) for r in results)
            for cat_name, group_name, amount in results:
                amount = abs(amount)
                pct = (amount / total * 100) if total > 0 else 0
                table.add_row(
                    cat_name,
                    f"[dim]{group_name}[/dim]",
                    f"${amount:,.2f}",
                    f"{pct:.1f}%"
                )

            table.add_row("", "", "", "")
            table.add_row("[bold]Total[/bold]", "", f"[bold]${total:,.2f}[/bold]", "100%")

        console.print(table)


@reports_group.command()
@click.option("--months", "-m", type=int, default=6, help="Number of months")
def trends(months):
    """Show spending trends over time."""
    with get_session() as session:
        today = date.today()

        # Build list of months
        month_list = []
        current = date(today.year, today.month, 1)
        for _ in range(months):
            month_list.append(current)
            if current.month == 1:
                current = date(current.year - 1, 12, 1)
            else:
                current = date(current.year, current.month - 1, 1)

        month_list.reverse()

        table = Table(title=f"Monthly Spending Trends ({months} months)")
        table.add_column("Month")
        table.add_column("Income", justify="right")
        table.add_column("Spending", justify="right")
        table.add_column("Net", justify="right")

        for month in month_list:
            if month.month == 12:
                next_month = date(month.year + 1, 1, 1)
            else:
                next_month = date(month.year, month.month + 1, 1)

            # Income
            income = (
                session.query(func.coalesce(func.sum(Transaction.amount), 0))
                .join(Account)
                .filter(Account.is_on_budget == True)
                .filter(Transaction.amount > 0)
                .filter(Transaction.date >= month)
                .filter(Transaction.date < next_month)
                .scalar()
            ) or 0

            # Spending
            spending = (
                session.query(func.coalesce(func.sum(Transaction.amount), 0))
                .join(Account)
                .filter(Account.is_on_budget == True)
                .filter(Transaction.amount < 0)
                .filter(Transaction.date >= month)
                .filter(Transaction.date < next_month)
                .scalar()
            ) or 0

            net = income + spending  # spending is negative

            net_str = f"${net:,.2f}" if net >= 0 else f"[red]-${abs(net):,.2f}[/red]"

            table.add_row(
                month.strftime("%b %Y"),
                f"[green]${income:,.2f}[/green]",
                f"[red]${abs(spending):,.2f}[/red]",
                net_str
            )

        console.print(table)


@reports_group.command()
def summary():
    """Show overall budget summary."""
    with get_session() as session:
        today = date.today()
        month_start = date(today.year, today.month, 1)

        if today.month == 12:
            next_month = date(today.year + 1, 1, 1)
        else:
            next_month = date(today.year, today.month + 1, 1)

        # This month's income
        income = (
            session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account)
            .filter(Account.is_on_budget == True)
            .filter(Transaction.amount > 0)
            .filter(Transaction.date >= month_start)
            .filter(Transaction.date < next_month)
            .scalar()
        ) or 0

        # This month's spending
        spending = (
            session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account)
            .filter(Account.is_on_budget == True)
            .filter(Transaction.amount < 0)
            .filter(Transaction.date >= month_start)
            .filter(Transaction.date < next_month)
            .scalar()
        ) or 0

        # Total transactions this month
        txn_count = (
            session.query(Transaction)
            .filter(Transaction.date >= month_start)
            .filter(Transaction.date < next_month)
            .count()
        )

        # Uncategorized
        uncategorized = (
            session.query(Transaction)
            .filter(Transaction.category_id == None)
            .count()
        )

        # Account totals
        total_balance = (
            session.query(func.coalesce(func.sum(Account.current_balance), 0))
            .filter(Account.is_closed == False)
            .filter(Account.is_on_budget == True)
            .scalar()
        ) or 0

        console.print(Panel(f"[bold]Budget Summary - {today.strftime('%B %Y')}[/bold]"))
        console.print()
        console.print(f"  Income:         [green]${income:>12,.2f}[/green]")
        console.print(f"  Spending:       [red]${abs(spending):>12,.2f}[/red]")
        console.print(f"  Net:            ${income + spending:>12,.2f}")
        console.print()
        console.print(f"  Transactions:   {txn_count:>12}")
        if uncategorized > 0:
            console.print(f"  Uncategorized:  [yellow]{uncategorized:>12}[/yellow]")
        console.print()
        console.print(f"  Account Total:  ${total_balance:>12,.2f}")


@reports_group.command()
@click.argument("category_name")
@click.option("--months", "-m", type=int, default=6, help="Number of months")
def category(category_name, months):
    """Show spending history for a specific category."""
    with get_session() as session:
        # Find category
        cat = (
            session.query(Category)
            .filter(Category.name.ilike(f"%{category_name}%"))
            .first()
        )

        if not cat:
            console.print(f"[red]Category '{category_name}' not found[/red]")
            return

        today = date.today()

        table = Table(title=f"Spending History: {cat.name}")
        table.add_column("Month")
        table.add_column("Amount", justify="right")
        table.add_column("Transactions", justify="right")

        totals = []
        current = date(today.year, today.month, 1)

        for _ in range(months):
            if current.month == 12:
                next_month = date(current.year + 1, 1, 1)
            else:
                next_month = date(current.year, current.month + 1, 1)

            amount = (
                session.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(Transaction.category_id == cat.id)
                .filter(Transaction.amount < 0)
                .filter(Transaction.date >= current)
                .filter(Transaction.date < next_month)
                .scalar()
            ) or 0

            count = (
                session.query(Transaction)
                .filter(Transaction.category_id == cat.id)
                .filter(Transaction.date >= current)
                .filter(Transaction.date < next_month)
                .count()
            )

            totals.append(abs(amount))

            table.add_row(
                current.strftime("%b %Y"),
                f"${abs(amount):,.2f}",
                str(count)
            )

            # Move to previous month
            if current.month == 1:
                current = date(current.year - 1, 12, 1)
            else:
                current = date(current.year, current.month - 1, 1)

        console.print(table)

        if totals:
            avg = sum(totals) / len(totals)
            console.print(f"\n[bold]Average:[/bold] ${avg:,.2f}/month")
