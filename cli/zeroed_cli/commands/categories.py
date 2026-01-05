"""
Category management commands.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ..core.database import get_session
from ..core.models import CategoryGroup, Category

console = Console()


@click.group(name="categories")
def categories_group():
    """Manage budget categories."""
    pass


@categories_group.command()
@click.option("--tree", "as_tree", is_flag=True, help="Show as tree structure")
def list(as_tree):
    """List all categories."""
    with get_session() as session:
        groups = (
            session.query(CategoryGroup)
            .filter(CategoryGroup.is_hidden == False)
            .order_by(CategoryGroup.sort_order)
            .all()
        )

        if not groups:
            console.print("[yellow]No categories found[/yellow]")
            return

        if as_tree:
            tree = Tree("[bold]Budget Categories[/bold]")
            for group in groups:
                branch = tree.add(f"[bold cyan]{group.name}[/bold cyan]")
                for cat in group.categories:
                    if not cat.is_hidden:
                        branch.add(cat.name)
            console.print(tree)
        else:
            table = Table(title="Budget Categories")
            table.add_column("Group")
            table.add_column("Category")
            table.add_column("ID", justify="right")

            for group in groups:
                first = True
                for cat in group.categories:
                    if not cat.is_hidden:
                        table.add_row(
                            f"[bold]{group.name}[/bold]" if first else "",
                            cat.name,
                            str(cat.id)
                        )
                        first = False

            console.print(table)


@categories_group.command()
@click.argument("group_name")
def create_group(group_name):
    """Create a new category group."""
    with get_session() as session:
        existing = session.query(CategoryGroup).filter(CategoryGroup.name == group_name).first()
        if existing:
            console.print(f"[red]Category group '{group_name}' already exists[/red]")
            return

        # Get max sort order
        max_order = session.query(CategoryGroup).count()

        group = CategoryGroup(name=group_name, sort_order=max_order)
        session.add(group)
        session.commit()

        console.print(f"[green]Created category group '{group_name}'[/green]")


@categories_group.command()
@click.argument("category_name")
@click.option("--group", "-g", required=True, help="Category group name")
def create(category_name, group):
    """Create a new category in a group."""
    with get_session() as session:
        # Find the group
        cat_group = session.query(CategoryGroup).filter(CategoryGroup.name.ilike(group)).first()
        if not cat_group:
            console.print(f"[red]Category group '{group}' not found[/red]")
            console.print("Available groups:")
            for g in session.query(CategoryGroup).all():
                console.print(f"  - {g.name}")
            return

        # Check if category already exists in this group
        existing = (
            session.query(Category)
            .filter(Category.group_id == cat_group.id)
            .filter(Category.name == category_name)
            .first()
        )
        if existing:
            console.print(f"[red]Category '{category_name}' already exists in {group}[/red]")
            return

        # Get max sort order in group
        max_order = (
            session.query(Category)
            .filter(Category.group_id == cat_group.id)
            .count()
        )

        category = Category(
            group_id=cat_group.id,
            name=category_name,
            sort_order=max_order
        )
        session.add(category)
        session.commit()

        console.print(f"[green]Created category '{category_name}' in {cat_group.name}[/green]")


@categories_group.command()
@click.argument("category_name")
@click.argument("new_name")
def rename(category_name, new_name):
    """Rename a category."""
    with get_session() as session:
        category = session.query(Category).filter(Category.name.ilike(category_name)).first()

        if not category:
            console.print(f"[red]Category '{category_name}' not found[/red]")
            return

        old_name = category.name
        category.name = new_name
        session.commit()

        console.print(f"[green]Renamed '{old_name}' to '{new_name}'[/green]")


@categories_group.command()
@click.argument("category_name")
def hide(category_name):
    """Hide a category (keep history but remove from budget)."""
    with get_session() as session:
        category = session.query(Category).filter(Category.name.ilike(category_name)).first()

        if not category:
            console.print(f"[red]Category '{category_name}' not found[/red]")
            return

        category.is_hidden = True
        session.commit()

        console.print(f"[green]Hidden category '{category_name}'[/green]")


@categories_group.command()
@click.argument("category_name")
def unhide(category_name):
    """Unhide a category."""
    with get_session() as session:
        category = (
            session.query(Category)
            .filter(Category.name.ilike(category_name))
            .filter(Category.is_hidden == True)
            .first()
        )

        if not category:
            console.print(f"[red]Hidden category '{category_name}' not found[/red]")
            return

        category.is_hidden = False
        session.commit()

        console.print(f"[green]Unhidden category '{category_name}'[/green]")
