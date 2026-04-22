import "./globals.css";

export const metadata = {
  title: "CompliFlow - Execution Control Layer",
  description: "Programmable execution control layer on Yellow Network with deterministic compliance"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=Figtree:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans">
        <div className="fixed inset-0 bg-gradient-to-br from-background via-surface to-background -z-10" />
        <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-accent-gold/10 via-transparent to-transparent -z-10" />
        {children}
      </body>
    </html>
  );
}
