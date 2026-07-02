import "server-only"
import { prisma } from "@/lib/db"

export interface DocSummary {
  slug: string
  title: string
  category: string
  order: number
  updatedAt: Date
}

export interface DocFull extends DocSummary {
  content: string
}

export async function listDocs(): Promise<DocSummary[]> {
  return prisma.doc.findMany({
    orderBy: [{ category: "asc" }, { order: "asc" }],
    select: { slug: true, title: true, category: true, order: true, updatedAt: true },
  })
}

export async function getDoc(slug: string): Promise<DocFull | null> {
  return prisma.doc.findUnique({ where: { slug } })
}

export async function createDoc(input: { slug: string; title: string; category: string; content: string; order?: number }) {
  return prisma.doc.create({
    data: {
      slug: input.slug,
      title: input.title,
      category: input.category,
      content: input.content,
      order: input.order ?? 0,
    },
  })
}

export async function updateDoc(
  slug: string,
  patch: Partial<{ title: string; content: string; category: string; order: number }>,
) {
  return prisma.doc.update({ where: { slug }, data: patch })
}

export async function deleteDoc(slug: string) {
  return prisma.doc.delete({ where: { slug } })
}
