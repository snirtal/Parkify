import { Environment, Lightformer } from '@react-three/drei'

export function StudioEnvironment3D() {
  return (
    <Environment resolution={128} frames={1}>
      {/* Overhead broad showroom softbox for crisp hood/roof highlights */}
      <Lightformer
        form="rect"
        intensity={3.2}
        color="#f8fafc"
        position={[0, 8, 0]}
        rotation={[Math.PI / 2, 0, 0]}
        scale={[14, 10, 1]}
      />
      {/* Left neon purple architectural rim strip */}
      <Lightformer
        form="rect"
        intensity={2.6}
        color="#c084fc"
        position={[-9, 3, -2]}
        rotation={[0, Math.PI / 2, 0]}
        scale={[12, 3, 1]}
      />
      {/* Right electric cyan rim strip */}
      <Lightformer
        form="rect"
        intensity={2.4}
        color="#22d3ee"
        position={[9, 3, 2]}
        rotation={[0, -Math.PI / 2, 0]}
        scale={[12, 3, 1]}
      />
      {/* Front subtle fill strip */}
      <Lightformer
        form="rect"
        intensity={1.6}
        color="#93c5fd"
        position={[0, 2.5, 10]}
        rotation={[0, Math.PI, 0]}
        scale={[10, 2.5, 1]}
      />
    </Environment>
  )
}
