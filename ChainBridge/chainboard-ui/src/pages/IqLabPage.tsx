/**
 * IQ Lab Page
 *
 * Dedicated page for ChainIQ ML debugging and testing.
 * Wraps the IqLabPanel component with appropriate page-level layout.
 *
 * @module pages/IqLabPage
 */

import IqLabPanel from "../features/chainiq/IqLabPanel";

export default function IqLabPage(): JSX.Element {
  return <IqLabPanel />;
}
