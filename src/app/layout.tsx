import type { ReactNode } from "react";
import "./globals.css";
import { GoogleAnalytics } from "@next/third-parties/google";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME || "My LEGO Guide";
const siteDescription = process.env.NEXT_PUBLIC_SITE_DESCRIPTION || "Demand-driven LEGO buying guides and product content.";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://mylegoguide.com";

export const metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: siteName,
    template: `%s | ${siteName}`
  },
  description: siteDescription,
  openGraph: {
    siteName,
    type: "website",
    url: siteUrl
  },
  twitter: {
    card: "summary_large_image",
    title: siteName,
    description: siteDescription
  }
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        {children}
        {process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID ? <GoogleAnalytics gaId={process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID} /> : null}
      </body>
    </html>
  );
}
