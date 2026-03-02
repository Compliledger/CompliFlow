export const metadata = {
  title: "CompliFlow",
  description: "Programmable execution control layer on Yellow Network"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "sans-serif", background: "#0f172a", color: "white" }}>
        {children}
      </body>
    </html>
  );
}
