import type { APIRoute } from "astro";
import { SEO_ROUTES } from "../seo/routes";

export const GET: APIRoute = ({ site }) => {
  const urls = SEO_ROUTES.map((route) => {
    const location = new URL(route.publicPath, site).href;
    return `  <url><loc>${location}</loc></url>`;
  }).join("\n");
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
  return new Response(body, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
