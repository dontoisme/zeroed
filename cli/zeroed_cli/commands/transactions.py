"""
Transaction management commands.
"""

import click
from datetime import date, datetime
from rich.console import Console
from rich.table import Table

from ..core.database import get_session
from ..core.models import Transaction, Account, Category, Payee, TransactionType

console = Console()


@click.group(name="transactions")
def transactions_group():
    """View and manage transactions."""
    pass


@transactions_group.command()
@click.option("--account", "-a", help="Filter by account name")
@click.option("--category", "-c", help="Filter by category name")
@click.option("--month", "-m", help="Filter by month (YYYY-MM)")
@click.option("--uncategorized", "-u", is_flag=True, help="Show only uncategorized")
@click.option("--limit", "-n", type=int, default=50, help="Number of transactions to show")
def list(account, category, month, uncategorized, limit):
    """List transactions."""
    with get_session() as session:
        query = session.query(Transaction).order_by(Transaction.date.desc())

        if account:
            acc = session.query(Account).filter(Account.name.ilike(f"%{account}%")).first()
            if acc:
                query = query.filter(Transaction.account_id == acc.id)
            else:
                console.print(f"[red]Account '{account}' not found[/red]")
                return

        if category:
            cat = session.query(Category).filter(Category.name.ilike(f"%{category}%")).first()
            if cat:
                query = query.filter(Transaction.category_id == cat.id)
            else:
                console.print(f"[red]Category '{category}' not found[/red]")
                return

        if month:
            try:
                year, mon = map(int, month.split("-"))
                start = date(year, mon, 1)
                if mon == 12:
                    end = date(year + 1, 1, 1)
                else:
                    end = date(year, mon + 1, 1)
                query = query.filter(Transaction.date >= start, Transaction.date < end)
            except ValueError:
                console.print("[red]Invalid month format. Use YYYY-MM[/red]")
                return

        if uncategorized:
            query = query.filter(Transaction.category_id == None)

        transactions = query.limit(limit).all()

        if not transactions:
            console.print("[yellow]No transactions found[/yellow]")
            return

        table = Table(title=f"Transactions (showing {len(transactions)})")
        table.add_column("Date")
        table.add_column("Account")
        table.add_column("Payee")
        table.add_column("Category")
        table.add_column("Amount", justify="right")
        table.add_column("Cleared")

        for txn in transactions:
            amount = txn.amount
            if amount < 0:
                amount_str = f"[red]-${abs(amount):,.2f}[/red]"
            else:
                amount_str = f"[green]+${amount:,.2f}[/green]"

            category_name = txn.category.name if txn.category else "[dim]Uncategorized[/dim]"
            payee_name = txn.payee.name if txn.payee else txn.raw_payee_name or "-"

            table.add_row(
                txn.date.strftime("%Y-%m-%d"),
                txn.account.name[:15],
                payee_name[:25],
                category_name[:20],
                amount_str,
                "[green]C[/green]" if txn.is_cleared else "[dim]-[/dim]"
            )

        console.print(table)


@transactions_group.command()
@click.argument("account_name")
@click.argument("amount", type=float)
@click.option("--payee", "-p", required=True, help="Payee name")
@click.option("--category", "-c", help="Category name")
@click.option("--date", "-d", "txn_date", help="Transaction date (YYYY-MM-DD)")
@click.option("--memo", "-m", help="Memo/notes")
def add(account_name, amount, payee, category, txn_date, memo):
    """Add a manual transaction."""
    with get_session() as session:
        # Find account
        account = session.query(Account).filter(Account.name.ilike(f"%{account_name}%")).first()
        if not account:
            console.print(f"[red]Account '{account_name}' not found[/red]")
            return

        # Find or create payee
        payee_obj = session.query(Payee).filter(Payee.name.ilike(payee)).first()
        if not payee_obj:
            payee_obj = Payee(name=payee)
            session.add(payee_obj)
            session.flush()

        # Find category if provided
        category_id = None
        if category:
            cat = session.query(Category).filter(Category.name.ilike(f"%{category}%")).first()
            if cat:
                category_id = cat.id
            else:
                console.print(f"[yellow]Category '{category}' not found, leaving uncategorized[/yellow]")

        # Parse date
        if txn_date:
            try:
                txn_date = datetime.strptime(txn_date, "%Y-%m-%d").date()
            except ValueError:
                console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
                return
        else:
            txn_date = date.today()

        # Create transaction
        txn = Transaction(
            account_id=account.id,
            category_id=category_id,
            payee_id=payee_obj.id,
            date=txn_date,
            amount=amount,
            transaction_type=TransactionType.INFLOW if amount > 0 else TransactionType.OUTFLOW,
            memo=memo,
            raw_payee_name=payee,
        )
        session.add(txn)

        # Update account balance
        account.current_balance += amount

        session.commit()

        console.print(f"[green]Added transaction: {payee} ${amount:,.2f}[/green]")


@transactions_group.command()
@click.argument("transaction_id", type=int)
@click.argument("category_name")
def categorize(transaction_id, category_name):
    """Categorize a transaction."""
    with get_session() as session:
        txn = session.query(Transaction).get(transaction_id)
        if not txn:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
            return

        category = session.query(Category).filter(Category.name.ilike(f"%{category_name}%")).first()
        if not category:
            console.print(f"[red]Category '{category_name}' not found[/red]")
            return

        txn.category_id = category.id
        session.commit()

        console.print(f"[green]Categorized as '{category.name}'[/green]")


@transactions_group.command()
@click.argument("transaction_id", type=int)
def clear(transaction_id):
    """Mark a transaction as cleared."""
    with get_session() as session:
        txn = session.query(Transaction).get(transaction_id)
        if not txn:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
            return

        txn.is_cleared = True
        txn.account.cleared_balance += txn.amount
        session.commit()

        console.print("[green]Transaction marked as cleared[/green]")


@transactions_group.command()
def uncategorized():
    """Show count of uncategorized transactions."""
    with get_session() as session:
        count = session.query(Transaction).filter(Transaction.category_id == None).count()

        if count == 0:
            console.print("[green]All transactions are categorized![/green]")
        else:
            console.print(f"[yellow]{count} uncategorized transactions[/yellow]")
            console.print("Use 'zeroed transactions list --uncategorized' to see them")
