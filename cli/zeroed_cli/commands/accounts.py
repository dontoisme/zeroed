"""
Account management commands.
"""

import click
from rich.console import Console
from rich.table import Table

from ..core.database import get_session
from ..core.models import Account, AccountType

console = Console()


@click.group(name="accounts")
def accounts_group():
    """Manage bank accounts and credit cards."""
    pass


@accounts_group.command()
def list():
    """List all accounts."""
    with get_session() as session:
        accounts = session.query(Account).filter(Account.is_closed == False).all()

        if not accounts:
            console.print("[yellow]No accounts found. Create one with 'zeroed accounts create'[/yellow]")
            return

        table = Table(title="Accounts")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Institution")
        table.add_column("Balance", justify="right")
        table.add_column("On Budget")

        for account in accounts:
            balance = account.current_balance
            balance_str = f"${balance:,.2f}" if balance >= 0 else f"[red]-${abs(balance):,.2f}[/red]"

            table.add_row(
                account.name,
                account.account_type.value.replace("_", " ").title(),
                account.institution or "-",
                balance_str,
                "[green]Yes[/green]" if account.is_on_budget else "[dim]No[/dim]"
            )

        console.print(table)


@accounts_group.command()
@click.argument("name")
@click.option(
    "--type", "-t",
    "account_type",
    type=click.Choice(["checking", "savings", "credit_card", "cash", "investment"]),
    required=True,
    help="Account type"
)
@click.option("--institution", "-i", help="Bank or institution name")
@click.option("--balance", "-b", type=float, default=0, help="Starting balance")
@click.option("--off-budget", is_flag=True, help="Track but don't include in budget")
def create(name, account_type, institution, balance, off_budget):
    """Create a new account."""
    with get_session() as session:
        # Check if account already exists
        existing = session.query(Account).filter(Account.name == name).first()
        if existing:
            console.print(f"[red]Account '{name}' already exists[/red]")
            return

        # Map string to enum
        type_map = {
            "checking": AccountType.CHECKING,
            "savings": AccountType.SAVINGS,
            "credit_card": AccountType.CREDIT_CARD,
            "cash": AccountType.CASH,
            "investment": AccountType.INVESTMENT,
        }

        account = Account(
            name=name,
            account_type=type_map[account_type],
            institution=institution,
            current_balance=balance,
            cleared_balance=balance,
            is_on_budget=not off_budget,
        )
        session.add(account)
        session.commit()

        console.print(f"[green]Created account '{name}'[/green]")
        console.print(f"  Type: {account_type.replace('_', ' ').title()}")
        console.print(f"  Balance: ${balance:,.2f}")
        if institution:
            console.print(f"  Institution: {institution}")


@accounts_group.command()
@click.argument("name")
def show(name):
    """Show account details."""
    with get_session() as session:
        account = session.query(Account).filter(Account.name.ilike(name)).first()

        if not account:
            console.print(f"[red]Account '{name}' not found[/red]")
            return

        console.print(f"\n[bold]{account.name}[/bold]")
        console.print(f"  Type: {account.account_type.value.replace('_', ' ').title()}")
        if account.institution:
            console.print(f"  Institution: {account.institution}")
        console.print(f"  Current Balance: ${account.current_balance:,.2f}")
        console.print(f"  Cleared Balance: ${account.cleared_balance:,.2f}")
        console.print(f"  On Budget: {'Yes' if account.is_on_budget else 'No'}")
        console.print(f"  Transactions: {len(account.transactions)}")


@accounts_group.command()
@click.argument("name")
def close(name):
    """Close an account (hide from list)."""
    with get_session() as session:
        account = session.query(Account).filter(Account.name.ilike(name)).first()

        if not account:
            console.print(f"[red]Account '{name}' not found[/red]")
            return

        if account.current_balance != 0:
            console.print(f"[yellow]Warning: Account has balance of ${account.current_balance:,.2f}[/yellow]")
            if not click.confirm("Close anyway?"):
                return

        account.is_closed = True
        session.commit()

        console.print(f"[green]Closed account '{name}'[/green]")


@accounts_group.command()
@click.option("--all", "show_all", is_flag=True, help="Include closed accounts")
def balances(show_all):
    """Show account balances summary."""
    with get_session() as session:
        query = session.query(Account)
        if not show_all:
            query = query.filter(Account.is_closed == False)

        accounts = query.all()

        if not accounts:
            console.print("[yellow]No accounts found[/yellow]")
            return

        # Group by type
        by_type = {}
        for account in accounts:
            type_name = account.account_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(account)

        total_assets = 0
        total_liabilities = 0

        for type_name, type_accounts in by_type.items():
            console.print(f"\n[bold]{type_name.replace('_', ' ').title()}[/bold]")
            for account in type_accounts:
                balance = account.current_balance
                if account.account_type == AccountType.CREDIT_CARD:
                    # Credit card balances are typically negative (you owe)
                    total_liabilities += abs(balance) if balance < 0 else 0
                else:
                    total_assets += balance

                balance_str = f"${balance:,.2f}" if balance >= 0 else f"-${abs(balance):,.2f}"
                status = " [dim](closed)[/dim]" if account.is_closed else ""
                console.print(f"  {account.name}: {balance_str}{status}")

        console.print(f"\n[bold]Net Worth: ${total_assets - total_liabilities:,.2f}[/bold]")
