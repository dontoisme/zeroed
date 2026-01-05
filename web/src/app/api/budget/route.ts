import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { startOfMonth, endOfMonth, addMonths, format } from "date-fns";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const monthParam = searchParams.get("month");

  // Parse month or use current
  const monthDate = monthParam ? new Date(monthParam + "-01") : new Date();
  const monthStart = startOfMonth(monthDate);
  const monthEnd = endOfMonth(monthDate);
  const nextMonthStart = addMonths(monthStart, 1);

  // Get all category groups with categories
  const groups = await prisma.categoryGroup.findMany({
    where: { isHidden: false },
    orderBy: { sortOrder: "asc" },
    include: {
      categories: {
        where: { isHidden: false },
        orderBy: { sortOrder: "asc" },
        include: {
          budgetEntries: {
            where: { month: monthStart },
          },
          goal: true,
          transactions: {
            where: {
              date: {
                gte: monthStart,
                lt: nextMonthStart,
              },
            },
          },
        },
      },
    },
  });

  // Calculate totals for each category
  const budgetData = groups.map((group) => ({
    id: group.id,
    name: group.name,
    categories: group.categories.map((cat) => {
      const budgeted = cat.budgetEntries[0]?.budgeted || 0;
      const activity = cat.transactions.reduce((sum, t) => sum + t.amount, 0);
      const available = budgeted + activity; // activity is negative for spending

      return {
        id: cat.id,
        name: cat.name,
        budgeted,
        activity,
        available,
        goal: cat.goal
          ? {
              type: cat.goal.goalType,
              target: cat.goal.targetAmount,
              targetDate: cat.goal.targetDate,
            }
          : null,
      };
    }),
  }));

  // Calculate ready to assign
  const inflows = await prisma.transaction.aggregate({
    _sum: { amount: true },
    where: {
      amount: { gt: 0 },
      date: { gte: monthStart, lt: nextMonthStart },
      account: { isOnBudget: true },
    },
  });

  const totalBudgeted = await prisma.budgetEntry.aggregate({
    _sum: { budgeted: true },
    where: { month: monthStart },
  });

  // Calculate carryover from previous months
  const prevBudgeted = await prisma.budgetEntry.aggregate({
    _sum: { budgeted: true },
    where: { month: { lt: monthStart } },
  });

  const prevInflows = await prisma.transaction.aggregate({
    _sum: { amount: true },
    where: {
      amount: { gt: 0 },
      date: { lt: monthStart },
      account: { isOnBudget: true },
    },
  });

  const prevOutflows = await prisma.transaction.aggregate({
    _sum: { amount: true },
    where: {
      amount: { lt: 0 },
      date: { lt: monthStart },
      account: { isOnBudget: true },
    },
  });

  const carryover =
    (prevInflows._sum.amount || 0) +
    (prevOutflows._sum.amount || 0) -
    (prevBudgeted._sum.budgeted || 0);

  const readyToAssign =
    (inflows._sum.amount || 0) +
    carryover -
    (totalBudgeted._sum.budgeted || 0);

  return NextResponse.json({
    month: format(monthStart, "yyyy-MM"),
    readyToAssign,
    groups: budgetData,
  });
}
