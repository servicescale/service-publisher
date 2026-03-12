import { notFound } from "next/navigation";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SiteRepository } from "@/lib/repositories/site-repository";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: { slug: string } }) {
  const repository = new SiteRepository(createSupabaseServerClient());
  const post = await repository.getPublishedPost(params.slug);
  if (!post) {
    return { title: "Not found" };
  }
  return {
    title: post.title,
    description: post.meta_description ?? undefined
  };
}

export default async function PostPage({ params }: { params: { slug: string } }) {
  const repository = new SiteRepository(createSupabaseServerClient());
  const post = await repository.getPublishedPost(params.slug);

  if (!post) {
    notFound();
  }

  return (
    <main className="shell">
      <article className="article">
        <p className="eyebrow">{post.pillar?.replace(/_/g, " ") ?? "guide"}</p>
        <h1>{post.title}</h1>
        {post.meta_description ? <p className="deck">{post.meta_description}</p> : null}
        <div className="article-body">
          <Markdown remarkPlugins={[remarkGfm]}>{post.content_md}</Markdown>
        </div>
      </article>
    </main>
  );
}
