# VR Fix Plan: Controller Ray Fallback + Shelf Intersection

## Current State Analysis

**Shelf intersection (Fix #1)**: Already correct at line 510:
```javascript
const shelfHits = raycaster.intersectObjects(shelfGroup.children, true);
```
No change needed — the working version is already in place.

**Controller ray (Fix #2)**: Missing camera fallback at lines 465-470. When controller matrix is identity (emulator / hand-tracking mode), origin is (0,0,0) and ray points down -Z, missing the shelf entirely.

---

## Required Fix: getControllerRay Camera Fallback

**Find** (lines 465-470):
```javascript
function getControllerRay(ctrl) {
  const tempMatrix = new THREE.Matrix4().identity().extractRotation(ctrl.matrixWorld);
  const origin = new THREE.Vector3().setFromMatrixPosition(ctrl.matrixWorld);
  const dir = new THREE.Vector3(0, 0, -1).applyMatrix4(tempMatrix).normalize();
  return { origin, dir };
}
```

**Replace with**:
```javascript
function getControllerRay(ctrl) {
  const tempMatrix = new THREE.Matrix4().identity().extractRotation(ctrl.matrixWorld);
  const origin = new THREE.Vector3().setFromMatrixPosition(ctrl.matrixWorld);
  const dir = new THREE.Vector3(0, 0, -1).applyMatrix4(tempMatrix).normalize();
  // If controller matrix is identity (emulator / hand-tracking), fall back to camera gaze ray
  if (origin.lengthSq() < 0.0001) {
    camera.getWorldPosition(origin);
    camera.getWorldDirection(dir);
  }
  return { origin, dir };
}
```

---

## Validation

- [ ] Controller ray uses camera gaze when origin ≈ (0,0,0) (emulator/hand-tracking)
- [ ] Controller ray uses controller pose when origin is valid (physical controllers)
- [ ] Shelf pinch works in emulator via camera gaze ray
- [ ] No syntax errors