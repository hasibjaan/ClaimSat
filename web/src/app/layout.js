import { Inter, Noto_Sans_Kannada } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const notoKannada = Noto_Sans_Kannada({
  variable: "--font-noto-kannada",
  subsets: ["kannada"],
  preload: false,
});

export const metadata = {
  title: "ClaimSat",
  description:
    "Satellite evidence for crop insurance claims: draw your plot, see the damage, get a report in English and Kannada.",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${notoKannada.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col font-sans">
        <div className="flex flex-1 flex-col">{children}</div>
        {/* Fixed height (h-11): the map screen sizes itself to 100dvh minus this footer. */}
        <footer className="flex h-11 shrink-0 items-center justify-center border-t border-line bg-surface px-4 text-center text-xs text-ink-muted sm:text-sm print:hidden">
          Supporting evidence, not an official loss assessment.
        </footer>
      </body>
    </html>
  );
}
