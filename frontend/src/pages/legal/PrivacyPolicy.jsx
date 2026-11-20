import "../../styles/PrivacyPolicy.css";
import { Link } from "react-router-dom";

function PrivacyPolicy()
{
    return (
        <main className="privacy-page">
            <h1>CareFlow Privacy Policy</h1>
            <p>Your privacy matters to us</p>
            <Link to="/login">Back to login</Link>
            <section className="privacy-section">
                <h2>Information We Collect</h2>
                <p>we just testing it :)</p>
            </section>
            <section className="privacy-section">
                <h2>How We Use Information</h2>
                <p>we just testing it :)</p>
            </section>
            <section className="privacy-section">
                <h2>Data Security</h2>
                <p>we just testing it :)</p>
            </section>
        </main>
    );
}
export default PrivacyPolicy;