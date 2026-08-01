// digital_twin.js - Three.js Digital Twin 3D
class DigitalTwin {
    constructor(canvasId, config) {
        this.canvas = document.getElementById(canvasId);
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, this.canvas.clientWidth / this.canvas.clientHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true });
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
        this.group = new THREE.Group();
        this.scene.add(this.group);
        this.sensores = [];
        this.isDragging = false;
        this.previousMouse = { x: 0, y: 0 };
        this.config = config || {};
        this.init();
    }

    init() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(5, 10, 7);
        this.scene.add(dirLight);
        this.camera.position.set(0, 3, 8);
        this.camera.lookAt(0, 0, 0);
        this.addBuilding();
        this.addControls();
        this.animate();
    }

    addBuilding() {
        const geom = new THREE.BoxGeometry(4, 3, 3);
        const mat = new THREE.MeshPhongMaterial({ color: 0xd4a853 });
        this.building = new THREE.Mesh(geom, mat);
        this.group.add(this.building);

        const roofGeom = new THREE.ConeGeometry(3, 1.5, 4);
        const roofMat = new THREE.MeshPhongMaterial({ color: 0xe94560 });
        const roof = new THREE.Mesh(roofGeom, roofMat);
        roof.position.y = 2.25;
        roof.rotation.y = Math.PI / 4;
        this.group.add(roof);

        const edgeGeom = new THREE.EdgesGeometry(geom);
        const edgeMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.3 });
        this.group.add(new THREE.LineSegments(edgeGeom, edgeMat));
    }

    addSensor(x, y, z, data) {
        const geom = new THREE.SphereGeometry(0.15, 16, 16);
        const color = data.alerta ? 0xe74c3c : 0x2ecc71;
        const mat = new THREE.MeshPhongMaterial({ color, emissive: color, emissiveIntensity: 0.5 });
        const sensor = new THREE.Mesh(geom, mat);
        sensor.position.set(x, y, z);
        sensor.userData = data;
        this.group.add(sensor);
        this.sensores.push(sensor);
        return sensor;
    }

    addControls() {
        this.canvas.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            this.previousMouse = { x: e.clientX, y: e.clientY };
        });
        this.canvas.addEventListener('mouseup', () => this.isDragging = false);
        this.canvas.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;
            const dx = e.clientX - this.previousMouse.x;
            const dy = e.clientY - this.previousMouse.y;
            this.group.rotation.y += dx * 0.01;
            this.group.rotation.x += dy * 0.01;
            this.previousMouse = { x: e.clientX, y: e.clientY };
        });
        this.canvas.addEventListener('wheel', (e) => {
            this.camera.position.z = Math.max(3, Math.min(15, this.camera.position.z + e.deltaY * 0.01));
        });
    }

    rotate(dir) { this.group.rotation.y += dir * 0.3; }
    zoom(dir) { this.camera.position.z = Math.max(3, Math.min(15, this.camera.position.z - dir * 1.5)); }
    reset() { this.group.rotation.set(0, 0, 0); this.camera.position.set(0, 3, 8); }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.group.rotation.y += 0.003;
        this.renderer.render(this.scene, this.camera);
    }

    resize() {
        this.camera.aspect = this.canvas.clientWidth / this.canvas.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
    }
}

window.DigitalTwin = DigitalTwin;