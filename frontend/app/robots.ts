import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/trust", "/security", "/.well-known/security.txt"],
      disallow: ["/api/", "/dashboard/"],
    },
    sitemap: "https://vulnova.com/sitemap.xml",
  };
}
