import React from "react";
import { Composition } from "remotion";
import { Satisfy2D, S2Props, metadatosSatisfy } from "./videos/satisfy2d/Satisfy2D";
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Satisfy2D" component={Satisfy2D} durationInFrames={1800} fps={60} width={1080} height={1920}
      defaultProps={{ plan: "particulas/demo/plan.json" } as S2Props} calculateMetadata={metadatosSatisfy as any} />
  </>
);
