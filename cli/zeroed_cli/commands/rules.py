"""
Categorization rules management commands.
"""

import click
from rich.console import Console
from rich.table import Table

from ..core.database import get_session
from ..core.models import PayeeMatchRule, Payee, Category, MatchType
from ..categorization.engine import CategorizationEngine

console = Console()


@click.group(name="rules")
def rules_group():
    """Manage auto-categorization rules."""
    pass


@rules_group.command()
def list():
    """List all categorization rules."""
    with get_session() as session:
        rules = (
            session.query(PayeeMatchRule)
            .order_by(PayeeMatchRule.priority.desc())
            .all()
        )

        if not rules:
            console.print("[yellow]No rules found. Create one with 'zeroed rules create'[/yellow]")
            return

        table = Table(title="Categorization Rules")
        table.add_column("ID", justify="right")
        table.add_column("Pattern")
        table.add_column("Match Type")
        table.add_column("Category")
        table.add_column("Priority", justify="right")

        for rule in rules:
            category_name = (
                rule.payee.default_category.name
                if rule.payee.default_category
                else "[dim]None[/dim]"
            )
            table.add_row(
                str(rule.id),
                rule.pattern,
                rule.match_type.value,
                category_name,
                str(rule.priority)
            )

        console.print(table)


@rules_group.command()
@click.argument("pattern")
@click.option("--category", "-c", required=True, help="Category to assign")
@click.option(
    "--type", "-t",
    "match_type",
    type=click.Choice(["contains", "starts_with", "exact", "regex"]),
    default="contains",
    help="Match type"
)
@click.option("--priority", "-p", type=int, default=0, help="Priority (higher = checked first)")
def create(pattern, category, match_type, priority):
    """Create a new categorization rule."""
    with get_session() as session:
        engine = CategorizationEngine(session)

        # Map string to enum
        type_map = {
            "contains": MatchType.CONTAINS,
            "starts_with": MatchType.STARTS_WITH,
            "exact": MatchType.EXACT,
            "regex": MatchType.REGEX,
        }

        try:
            rule = engine.create_rule(
                pattern=pattern,
                category_name=category,
                match_type=type_map[match_type],
                priority=priority
            )
            session.commit()

            console.print(f"[green]Created rule: '{pattern}' -> {category}[/green]")
            console.print(f"  Match type: {match_type}")
            console.print(f"  Priority: {priority}")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")


@rules_group.command()
@click.argument("rule_id", type=int)
def delete(rule_id):
    """Delete a categorization rule."""
    with get_session() as session:
        rule = session.query(PayeeMatchRule).get(rule_id)

        if not rule:
            console.print(f"[red]Rule {rule_id} not found[/red]")
            return

        pattern = rule.pattern
        session.delete(rule)
        session.commit()

        console.print(f"[green]Deleted rule '{pattern}'[/green]")


@rules_group.command()
@click.argument("pattern")
def test(pattern):
    """Test which rule matches a payee pattern."""
    with get_session() as session:
        engine = CategorizationEngine(session)

        category = engine.categorize(pattern)

        if category:
            console.print(f"[green]Match found![/green]")
            console.print(f"  '{pattern}' -> {category.name}")
        else:
            console.print(f"[yellow]No match for '{pattern}'[/yellow]")

            # Show suggestions
            suggestions = engine.suggest_categories(pattern)
            if suggestions:
                console.print("\nSuggested categories based on similar payees:")
                for cat in suggestions:
                    console.print(f"  - {cat.name}")


@rules_group.command()
def payees():
    """List all payees with their default categories."""
    with get_session() as session:
        payees = (
            session.query(Payee)
            .filter(Payee.default_category_id.isnot(None))
            .order_by(Payee.name)
            .all()
        )

        if not payees:
            console.print("[yellow]No payees with default categories[/yellow]")
            return

        table = Table(title="Payees with Default Categories")
        table.add_column("Payee")
        table.add_column("Default Category")
        table.add_column("Auto")

        for payee in payees:
            table.add_row(
                payee.name[:40],
                payee.default_category.name if payee.default_category else "-",
                "[green]Yes[/green]" if payee.auto_categorize else "[red]No[/red]"
            )

        console.print(table)


@rules_group.command()
@click.argument("payee_name")
@click.argument("category_name")
def set_payee(payee_name, category_name):
    """Set default category for a payee."""
    with get_session() as session:
        # Find category
        category = (
            session.query(Category)
            .filter(Category.name.ilike(f"%{category_name}%"))
            .first()
        )
        if not category:
            console.print(f"[red]Category '{category_name}' not found[/red]")
            return

        # Find or create payee
        payee = (
            session.query(Payee)
            .filter(Payee.name.ilike(payee_name))
            .first()
        )

        if payee:
            payee.default_category_id = category.id
            console.print(f"[green]Updated payee '{payee.name}' -> {category.name}[/green]")
        else:
            payee = Payee(
                name=payee_name,
                default_category_id=category.id,
                auto_categorize=True
            )
            session.add(payee)
            console.print(f"[green]Created payee '{payee_name}' -> {category.name}[/green]")

        session.commit()
